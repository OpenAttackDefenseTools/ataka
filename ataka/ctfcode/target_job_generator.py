import time
from asyncio import sleep
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ataka.common import database
from ataka.common.database.models import Job, JobExecutionStatus, Target, Execution
from ataka.common.queue import JobQueue, get_channel, JobMessage, JobAction
from .ctf import CTF
from ..common.database.models.exploit_history import ExploitHistory


class TargetJobGenerator:
    def __init__(self, ctf: CTF):
        self._ctf = ctf

    async def run_loop(self):
        async with await get_channel() as channel:
            job_queue = await JobQueue.get(channel)

            async with database.get_session() as session:
                # Get all queued jobs
                await job_queue.clear()
                get_future_jobs = select(Job) \
                    .where(Job.status.in_([JobExecutionStatus.QUEUED, JobExecutionStatus.RUNNING]))
                future_jobs = (await session.execute(get_future_jobs)).scalars()
                # cancel the jobs
                for job in future_jobs:
                    await job_queue.send_message(JobMessage(action=JobAction.CANCEL, job_id=job.id))

            while True:
                print("New tick")
                services = self._ctf.get_services()
                all_targets = self._ctf.get_targets()
                round_time = self._ctf.get_round_time()

                async with database.get_session() as session:
                    next_version = await session.execute(Target.version_seq)

                    job_list = []
                    for service, targets in all_targets.items():
                        if service not in services:
                            print(f"{service=} not in {services=}")
                            # TODO: log warning
                            continue

                        target_objs = [Target(version=next_version, ip=t["ip"], service=service, extra=t["extra"])
                                       for t in targets]
                        session.add_all(target_objs)

                        # if we have an exploit, submit a job for this service
                        get_exploits_for_service = select(ExploitHistory) \
                            .where(ExploitHistory.service == service) \
                            .options(
                                selectinload(ExploitHistory.exploits),
                                selectinload(ExploitHistory.exclusions))
                        exploit_list = (await session.execute(get_exploits_for_service)).scalars()
                        for history in exploit_list:
                            excluded_ips = set(x.target_ip for x in history.exclusions)
                            excluded_ips.update(self._ctf.get_static_exclusions())
                            history_target_objs = [t for t in target_objs if t.ip not in excluded_ips]
                            for exploit in [e for e in history.exploits if e.active]:
                                job_obj = Job(status=JobExecutionStatus.QUEUED, timeout=datetime.fromtimestamp(self._ctf.get_next_tick_start()),
                                              exploit=exploit)
                                session.add(job_obj)

                                session.add_all([Execution(job=job_obj, target=t,
                                                           status=JobExecutionStatus.QUEUED) for t in history_target_objs])

                                job_list += [job_obj]

                    await session.commit()

                    for job in job_list:
                        await job_queue.send_message(JobMessage(action=JobAction.QUEUE, job_id=job.id))

                # sleep until next tick
                next_tick = self._ctf.get_next_tick_start()
                diff = next_tick - time.time()
                if diff > 0:
                    await sleep(diff)
