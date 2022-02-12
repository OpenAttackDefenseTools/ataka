import asyncio
import os

from ataka.common import queue, database
from .ctf import CTF
from .flags import Flags


async def main():
    # load ctf-specific code
    ctf = CTF(os.environ["CTF"])

    # initialize connections
    await queue.connect()
    await database.connect()

    flags = Flags(ctf)
    flags_task = asyncio.create_task(flags.poll_and_submit_flags())
    await asyncio.gather(flags_task)


asyncio.run(main())