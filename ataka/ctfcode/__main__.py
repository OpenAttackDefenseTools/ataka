import asyncio
import os

from ataka.common import queue, database
from .ctf import CTF
from .flags import Flags
from .target_job_generator import TargetJobGenerator


async def main():
    # initialize connections
    await queue.connect()
    await database.connect()

    # load ctf-specific code
    ctf = CTF(os.environ["CTF"])
    flags = Flags(ctf)
    target_job_generator = TargetJobGenerator(ctf)

    reload_task = ctf.watch_for_reload()
    flags_task = flags.poll_and_submit_flags()
    output_task = flags.poll_and_parse_output()
    target_job_task = target_job_generator.run_loop()

    await asyncio.gather(reload_task, flags_task, output_task, target_job_task)


asyncio.run(main())