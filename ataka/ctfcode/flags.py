from asyncio import TimeoutError, sleep

from sqlalchemy.future import select

from ataka.common import queue, database
from ataka.common.database.models import Flag, FlagStatus
from .ctf import CTF
from ..common.queue import FlagQueue


class Flags:
    # A wrapper that loads the specified ctf by name, and wraps the api with support
    # for hot-reload.
    def __init__(self, ctf: CTF):
        self._ctf = ctf

    async def poll_and_submit_flags(self):
        channel = await queue.get_channel()
        flag_queue = await FlagQueue.get(channel)
        async with database.get_session() as session:
            while True:
                batchsize = self._ctf.get_flag_batchsize()
                ratelimit = self._ctf.get_flag_ratelimit()

                submitlist = []
                try:
                    async for flag in flag_queue.wait_for_messages(timeout=ratelimit):
                        print(f"Got flag {flag}")

                        stmt = select(Flag).where(Flag.id != flag.id and Flag.flag == flag.flag)
                        result = (await session.execute(stmt)).scalars().first()

                        # if there is already such a flag
                        # do not submit, but put in DUPLICATE in database
                        if result is None:
                            flag.status = FlagStatus.PENDING
                            submitlist += [flag]
                        else:
                            flag.status = FlagStatus.DUPLICATE

                        session.add(flag)
                        await session.commit()

                        if len(submitlist) >= batchsize:
                            break
                except TimeoutError:
                    pass

                if len(submitlist) > 0:
                    print(f"Submitting {len(submitlist)} flags")
                    statuslist = self._ctf.submit_flags([flag.flag for flag in submitlist])

                    for flag, status in zip(submitlist, statuslist):
                        flag.status = status
                    await session.commit()
                    await sleep(ratelimit)
