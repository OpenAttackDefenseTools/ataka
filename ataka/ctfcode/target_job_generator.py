import time
from asyncio import sleep

from sqlalchemy.future import select

from ataka.common import database
from ataka.common.database.models import Job, JobExecutionStatus, Target, Exploit, ExploitStatus
from ataka.common.queue import JobQueue, get_channel, JobMessage, JobAction
from .ctf import CTF


class TargetJobGenerator:
    def __init__(self, ctf: CTF):
        self._ctf = ctf

    async def run_loop(self):
        async with await get_channel() as channel:
            job_queue = await JobQueue.get(channel)

            async with database.get_session() as session:
                # Cancel all running jobs on scheduler restart
                await job_queue.clear()
                get_future_jobs = select(Job).where(
                    Job.status.in_([JobExecutionStatus.QUEUED, JobExecutionStatus.RUNNING]))
                future_jobs = (await session.execute(get_future_jobs)).scalars()
                for job in future_jobs:
                    await job_queue.send_message(JobMessage(action=JobAction.CANCEL, job_id=job.id))

                while True:
                    print("New tick")
                    services = self._ctf.get_services()
                    all_targets = self._ctf.get_targets()
                    round_time = self._ctf.get_round_time()

                    next_version = await session.execute(Target.version_seq)

                    job_ids = []
                    for service, targets in all_targets.items():
                        if service not in services:
                            # TODO: log warning
                            continue

                        target_objs = [Target(version=next_version, ip=t["ip"], service=service, extra=t["extra"])
                                       for t in targets]
                        session.add_all(target_objs)

                        # if we have an exploit, submit a job for this service
                        get_latest_exploit = select(Exploit) \
                            .where(Exploit.service == service) \
                            .where(Exploit.status == ExploitStatus.READY) \
                            .order_by(Exploit.version.desc()) \
                            .limit(1)
                        latest_exploit = (await session.execute(get_latest_exploit)).scalars().first()
                        if latest_exploit is None:
                            continue

                        job_obj = Job(status=JobExecutionStatus.QUEUED, lifetime=round_time, exploit=latest_exploit)
                        session.add(job_obj)
                        job_ids += [job_obj.id]
                    await session.commit()

                    for job_id in job_ids:
                        await job_queue.send_message(JobMessage(action=JobAction.QUEUE, job_id=job_id))

                    # sleep until next tick
                    next_tick = self._ctf.get_next_tick_start()
                    diff = next_tick - time.time()
                    if diff > 0:
                        await sleep(diff)
