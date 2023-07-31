import asyncio
import math
import os
import time
import traceback
from datetime import datetime
from typing import Optional

from aiodocker import DockerError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload

from ataka.common import database
from ataka.common.database.models import Job, Execution, Exploit
from ataka.common.queue import get_channel, JobQueue, JobAction, OutputQueue, OutputMessage
from .localdata import *


class BuildError(Exception):
    pass


class Jobs:
    def __init__(self, docker, exploits):
        self._docker = docker
        self._exploits = exploits
        self._jobs = {}

    async def poll_and_run_jobs(self):
        async with get_channel() as channel:
            job_queue = await JobQueue.get(channel)

            async for job_message in job_queue.wait_for_messages():
                match job_message.action:
                    case JobAction.CANCEL:
                        print(f"DEBUG: CURRENTLY RUNNING {len(self._jobs)}")
                        result = [(task, job) for task, job in self._jobs.items() if job.id == job_message.job_id]
                        if len(result) > 0:
                            task, job = result[0]
                            await task.cancel()
                    case JobAction.QUEUE:
                        job_execution = JobExecution(self._docker, self._exploits, channel, job_message.job_id)
                        task = asyncio.create_task(job_execution.run())

                        def on_done(job):
                            del self._jobs[job]

                        self._jobs[task] = job_execution
                        task.add_done_callback(on_done)


class JobExecution:
    def __init__(self, docker, exploits, channel, job_id: int):
        self.id = job_id
        self._docker = docker
        self._exploits = exploits
        self._channel = channel
        self._data_store = os.environ["DATA_STORE"]

    async def run(self):
        job = await self.fetch_job_from_database()
        if job is None:
            return

        exploit = job.exploit

        persist_dir = f"/data/persist/{exploit.docker_name}"
        host_persist_dir = f"{self._data_store}/persist/{exploit.docker_name}"
        host_shared_dir = f"{self._data_store}/shared/exploits"

        try:
            os.makedirs(persist_dir, exist_ok=True)
            container_ref = await self._docker.containers.create_or_replace(
                name=f"ataka-exploit-{exploit.docker_name}",
                config={
                    "Image": exploit.docker_id,
                    "Cmd": ["sleep", str(math.floor(job.timeout - time.time()))],
                    "AttachStdin": False,
                    "AttachStdout": False,
                    "AttachStderr": False,
                    "Tty": False,
                    "OpenStdin": False,
                    "StopSignal": "SIGKILL",
                    "HostConfig": {
                        "Mounts": [
                            {
                                "Type": "bind",
                                "Source": host_persist_dir,
                                "Target": "/persist",
                            },
                            {
                                "Type": "bind",
                                "Source": host_shared_dir,
                                "Target": "/shared",
                            }
                        ],
                        "CapAdd": ["NET_RAW"],
                        "NetworkMode": "container:ataka-exploit",
                        "CpusetCpus": os.environ.get('EXPLOIT_CPUSET', ''),
                    },
                },
            )

            await container_ref.start()
        except DockerError as exception:
            print(f"Got docker error for exploit {exploit.id} (service {exploit.service}) by {exploit.author}")
            print(traceback.format_exception(exception))
            for e in job.executions:
                e.status = JobExecutionStatus.FAILED
                e.stderr = str(exception)
            await self.submit_to_database(job.executions)
            raise exception

        execute_tasks = [self.docker_execute(container_ref, e) for e in job.executions]

        print(f"Starting {len(execute_tasks)} tasks for exploit {exploit.id} (service {exploit.service}) by {exploit.author}")

        # Execute all the exploits
        results = await asyncio.gather(*execute_tasks)

        # try:
        #    os.rmdir(persist_dir)
        # except (FileNotFoundError, OSError):
        #    pass

        await self.submit_to_database(results)
        # TODO: send to ctfconfig

    async def fetch_job_from_database(self) -> Optional[LocalJob]:
        async with database.get_session() as session:
            get_job = select(Job).where(Job.id == self.id).options(
                joinedload(Job.exploit).joinedload(Exploit.exploit_history), joinedload(Job.executions).joinedload(Execution.target)
            )
            job = (await session.execute(get_job)).unique().scalar_one()
            executions = job.executions

            time_left = job.timeout.timestamp() - time.time()
            if time_left < 0:
                job.status = JobExecutionStatus.TIMEOUT
                for e in executions:
                    e.status = JobExecutionStatus.TIMEOUT
                    e.stderr = "<EXECUTOR TIMEOUT HAPPENED>"
                await session.commit()
                return None

            local_exploit = await self._exploits.ensure_exploit(job.exploit)

            job.timeout = datetime.fromtimestamp(time.time() + time_left)
            if local_exploit.status is not LocalExploitStatus.FINISHED:
                print(f"Got build error for exploit {local_exploit.id} (service {local_exploit.service}) by {local_exploit.author}")
                print(f"   {local_exploit.build_output}")
                job.status = JobExecutionStatus.FAILED
                for e in executions:
                    e.status = JobExecutionStatus.FAILED
                    e.stderr = local_exploit.build_output
                await session.commit()
                return None

            job.status = JobExecutionStatus.RUNNING
            local_executions = []
            for e in executions:
                e.status = JobExecutionStatus.RUNNING
                local_executions += [
                    LocalExecution(e.id, local_exploit, LocalTarget(e.target.ip, e.target.extra), JobExecutionStatus.RUNNING)]

            await session.commit()

            # Convert data to local for usage without database
            return LocalJob(local_exploit, job.timeout.timestamp(), local_executions)

    async def submit_to_database(self, results: [LocalExecution]):
        local_executions = {e.database_id: e for e in results}
        status = JobExecutionStatus.FAILED if any([e.status == JobExecutionStatus.FAILED for e in results]) \
            else JobExecutionStatus.CANCELLED if any([e.status == JobExecutionStatus.CANCELLED for e in results]) \
            else JobExecutionStatus.FINISHED

        # submit results to database
        async with database.get_session() as session:
            get_job = select(Job).where(Job.id == self.id)
            job = (await session.execute(get_job)).scalar_one()
            job.status = status

            get_executions = select(Execution).where(Execution.job_id == self.id) \
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
                exec_ref = await container_ref.exec(cmd=execution.exploit.docker_cmd, workdir="/exploit", tty=False,
                                                    environment={
                                                        "ATAKA_CENTRAL_EXECUTION": "TRUE",
                                                        "TARGET_IP": execution.target.ip,
                                                        "TARGET_EXTRA": execution.target.extra,
                                                        "ATAKA_EXPLOIT_ID": execution.exploit.id,
                                                    })
                async with exec_ref.start(detach=False) as stream:
                    while True:
                        message = await stream.read_out()
                        if message is None:
                            break

                        yield message[0], message[1].decode()
            except DockerError as e:
                print(f"DOCKER EXECUTION ERROR for {execution.exploit.id} (service {execution.exploit.service}) " \
                      f"by {execution.exploit.author} against target {execution.target.ip}\n" \
                      f"{e.message}")
                msg = f"DOCKER EXECUTION ERROR: {e.message}"
                execution.status = JobExecutionStatus.FAILED
                execution.stderr += msg
                yield 2, msg


        output_queue = await OutputQueue.get(self._channel)

        async for (stream, output) in exec_in_container_and_poll_output():
            # collect output
            match stream:
                case 1:
                    execution.stdout += output
                case 2:
                    execution.stderr += output

            await output_queue.send_message(OutputMessage(execution.database_id, stream == 1, output))
        if execution.status in [JobExecutionStatus.QUEUED, JobExecutionStatus.RUNNING]:
            execution.status = JobExecutionStatus.FINISHED
        return execution
