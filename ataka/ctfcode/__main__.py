import asyncio
import os

from ataka.common import queue, database
from .ctf import CTF
from .flags import Flags


async def main():
    # initialize connections
    await queue.connect()
    await database.connect()

    # load ctf-specific code
    ctf = CTF(os.environ["CTF"])
    flags = Flags(ctf)

    reload_task = ctf.watch_for_reload()
    flags_task = flags.poll_and_submit_flags()
    await asyncio.gather(flags_task, reload_task)


asyncio.run(main())