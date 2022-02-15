import asyncio
import os

from aiodocker import Docker

from ataka.common import queue, database
from .exploits import Exploits
from .jobs import Jobs


async def main():
    # initialize connections
    await queue.connect()
    await database.connect()

    docker = Docker()

    # load ctf-specific code
    exploits = Exploits(docker)
    jobs = Jobs(docker, exploits)

    poll_task = jobs.poll_and_run_jobs()

    await asyncio.gather(poll_task)

    await docker.close()


asyncio.run(main())