import asyncio
import math
import os
import time
from typing import Optional

from aiodocker import DockerError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ataka.common import database
from ataka.common.database.models import Job, Execution
from ataka.common.queue import get_channel, JobQueue, JobAction
from .localdata import *
from ..common.queue.output import OutputQueue, OutputMessage


class BuildError(Exception):
    pass


class Jobs:
    def __init__(self, docker, exploits):
        self._docker = docker
        self._exploits = exploits
        self._jobs = []

    async def poll_and_run_jobs(self):
        async with await get_channel() as channel:
            job_queue = await JobQueue.get(channel)

            async for job_message in job_queue.wait_for_messages():
                match job_message.action:
                    case JobAction.CANCEL:
                        # TODO: do
                        pass
                    case JobAction.QUEUE:
                        job_execution = JobExecution(self._docker, self._exploits, channel, job_message.job_id)
                        self._jobs += [asyncio.create_task(job_execution.run())]


class JobExecution:
    def __init__(self, docker, exploits, channel, job_id: int):
        self._docker = docker
        self._exploits = exploits
        self._channel = channel
        self._job_id = job_id
        self._data_store = os.environ["DATA_STORE"]

    async def run(self):
        job = await self.fetch_job_from_database()
        if job is None:
            return

        exploit = job.exploit

        persist_dir = f"/data/persist/{exploit.file}"
        host_persist_dir = f"{self._data_store}/persist/{exploit.file}"

        try:
            os.makedirs(persist_dir, exist_ok=True)
            container_ref = await self._docker.containers.create_or_replace(name=f"ataka-exploit-{exploit.file}",
                                                                            config={
                                                                                "Image": exploit.docker_id,
                                                                                "Cmd": ["sleep", str(math.floor(
                                                                                    job.timeout - time.time()))],
                                                                                "AttachStdin": False,
                                                                                "AttachStdout": False,
                                                                                "AttachStderr": False,
                                                                                "Tty": False,
                                                                                "OpenStdin": False,
                                                                                "StopSignal": "SIGKILL",
                                                                                "HostConfig": {
                                                                                    "Mounts": [{
                                                                                        "Type": "bind",
                                                                                        "Source": host_persist_dir,
                                                                                        "Target": "/persist",
                                                                                    }]
                                                                                }
                                                                            })

            await container_ref.start()
        except (DockerError, Exception) as e:
            print(e)
            raise e

        execute_tasks = [self.docker_execute(container_ref, e) for e in job.executions]

        # Execute all the exploits
        results = await asyncio.gather(*execute_tasks)

        #try:
        #    os.rmdir(persist_dir)
        #except (FileNotFoundError, OSError):
        #    pass

        await self.submit_to_database(results)
        # TODO: send to ctfconfig

    async def fetch_job_from_database(self) -> Optional[LocalJob]:
        async with database.get_session() as session:
            get_job = select(Job).where(Job.id == self._job_id)
            job = (await session.execute(get_job)).scalar_one()
            get_executions = select(Execution).where(Execution.job_id == self._job_id) \
                .options(selectinload(Execution.target))
            executions = (await session.execute(get_executions)).scalars()

            if job.timeout.timestamp() - time.time() < 0:
                job.status = JobExecutionStatus.TIMEOUT
                for e in executions:
                    e.status = JobExecutionStatus.TIMEOUT
                await session.commit()
                # todo: handle timeout
                return None

            exploit = await self._exploits.ensure_exploit(job.exploit_id)
            # TODO: deal with this
            if exploit.status is not LocalExploitStatus.FINISHED:
                print(f"Got error exploit {exploit.build_output}")
                print(f"   {exploit}")
                job.status = JobExecutionStatus.FAILED
                for e in executions:
                    e.status = JobExecutionStatus.FAILED
                await session.commit()
                return None

            job.status = JobExecutionStatus.RUNNING
            local_executions = []
            for e in executions:
                e.status = JobExecutionStatus.RUNNING
                local_executions += [
                    LocalExecution(e.id, exploit, LocalTarget(e.target.ip, e.target.extra), JobExecutionStatus.RUNNING)]

            await session.commit()

            # Convert data to local for usage without database
            return LocalJob(exploit, job.timeout.timestamp(), local_executions)

    async def submit_to_database(self, results: [LocalExecution]):
        local_executions = {e.database_id: e for e in results}

        # submit results to database
        async with database.get_session() as session:
            get_job = select(Job).where(Job.id == self._job_id)
            job = (await session.execute(get_job)).scalar_one()
            job.status = LocalExploitStatus.FINISHED

            get_executions = select(Execution).where(Execution.job_id == self._job_id) \
                .options(selectinload(Execution.target))
            executions = (await session.execute(get_executions)).scalars()

            for execution in executions:
                local_execution = local_executions[execution.id]
                execution.status = local_execution.status
                execution.stdout = local_execution.stdout
                execution.stderr = local_execution.stderr

            await session.commit()

    async def docker_execute(self, container_ref, execution: LocalExecution) -> LocalExecution:
        async def exec_in_container_and_poll_output():
            try:
                exec_ref = await container_ref.exec(cmd=execution.exploit.docker_cmd, workdir="/exploit", tty=False, environment={
                    "TARGET_IP": execution.target.ip,
                    "TARGET_EXTRA": execution.target.extra,
                })
                async with exec_ref.start(detach=False) as stream:
                    while True:
                        message = await stream.read_out()
                        if message is None:
                            break

                        yield message[0], message[1].decode()
            except DockerError as e:
                yield 2, f"DOCKER EXECUTION ERROR: {e.message}"

        output_queue = await OutputQueue.get(self._channel)

        async for (stream, output) in exec_in_container_and_poll_output():
            # collect output
            match stream:
                case 1:
                    execution.stdout += output
                case 2:
                    execution.stderr += output

            await output_queue.send_message(OutputMessage(None, execution.database_id, stream == 1, output))
        execution.status = JobExecutionStatus.FINISHED
        return execution
