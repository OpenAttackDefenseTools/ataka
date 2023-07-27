import asyncio
import os
import signal

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

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGUSR1, ctf.reload)

    flags_task = flags.poll_and_submit_flags()
    output_task = flags.poll_and_parse_output()
    target_job_task = target_job_generator.run_loop()

    await asyncio.gather(flags_task, output_task, target_job_task)


asyncio.run(main())
