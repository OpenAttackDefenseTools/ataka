import time
from asyncio import sleep
from datetime import datetime
from functools import reduce

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ataka.common import database
from ataka.common.database.models import Job, Target, Execution, ExploitHistory
from ataka.common.queue import JobQueue, get_channel, JobMessage, JobAction
from ataka.common.job_execution_status import JobExecutionStatus
from .ctf import CTF


class TargetJobGenerator:
    def __init__(self, ctf: CTF):
        self._ctf = ctf

    async def run_loop(self):
        async with get_channel() as channel:
            job_queue = await JobQueue.get(channel)

            async with database.get_session() as session:
                # Get all queued jobs
                await job_queue.clear()
                get_future_jobs = select(Job) \
                    .where((Job.exploit_id != None) &
                           Job.status.in_([JobExecutionStatus.QUEUED, JobExecutionStatus.RUNNING]))
                future_jobs = (await session.execute(get_future_jobs)).scalars()
                # cancel the jobs
                for job in future_jobs:
                    await job_queue.send_message(JobMessage(action=JobAction.CANCEL, job_id=job.id))

            while True:
                if (sleep_duration := self._ctf.get_start_time() - time.time()) > 0:
                    print(f"CTF not started yet, sleeping for {int(sleep_duration)} seconds...")
                    await sleep(min(self._ctf.get_round_time(), sleep_duration))
                    continue

                print("New tick")
                all_targets = self._ctf.get_targets()

                async with database.get_session() as session:
                    next_version = await session.execute(Target.version_seq)

                    # if we have an exploit, submit a job for this service
                    get_exploits = select(ExploitHistory) \
                        .options(
                        selectinload(ExploitHistory.exploits),
                        selectinload(ExploitHistory.exclusions))
                    exploit_list = list((await session.execute(get_exploits)).scalars())
                    all_exploits = {exploit.service: [] for exploit in exploit_list}
                    for history in exploit_list:
                        all_exploits[history.service].append(history)

                    job_list = []
                    for service, targets in all_targets.items():
                        target_objs = [Target(version=next_version, ip=t["ip"], service=service, extra=t["extra"])
                                       for t in targets]
                        session.add_all(target_objs)

                        if service not in all_exploits:
                            continue

                        exploits_for_this_service = all_exploits[service]
                        del all_exploits[service]

                        for history in exploits_for_this_service:
                            excluded_ips = set(x.target_ip for x in history.exclusions)
                            excluded_ips.update(self._ctf.get_static_exclusions())
                            history_target_objs = [t for t in target_objs if t.ip not in excluded_ips]
                            for history in [e for e in history.exploits if e.active]:
                                job_obj = Job(status=JobExecutionStatus.QUEUED,
                                              timeout=datetime.fromtimestamp(self._ctf.get_next_tick_start()),
                                              exploit=history)
                                session.add(job_obj)

                                session.add_all([Execution(job=job_obj, target=t,
                                                           status=JobExecutionStatus.QUEUED) for t in
                                                 history_target_objs])

                                job_list += [job_obj]

                    for service, histories in all_exploits.items():
                        for history in histories:
                            print(f"WARNING: Got exploit history {history.id} for service {service} but no targets for this service.")

                    await session.commit()

                    for job in job_list:
                        await job_queue.send_message(JobMessage(action=JobAction.QUEUE, job_id=job.id))

                # sleep until next tick
                next_tick = self._ctf.get_next_tick_start()
                diff = next_tick - time.time()
                if diff > 0:
                    await sleep(diff)
