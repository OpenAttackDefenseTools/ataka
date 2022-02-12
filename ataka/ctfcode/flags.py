import asyncio

from sqlalchemy.future import select

from ataka.common import queue, database, flag_status
from ataka.common.database.model.flag import Flag
from .ctf import CTF


# A wrapper that loads the specified ctf by name, and wraps the api with support
# for hot-reload.
class Flags:
    def __init__(self, ctf: CTF):
        self._ctf = ctf

    async def poll_and_submit_flags(self):
        channel = await queue.get_channel()
        flags = await channel.declare_queue("flags", durable=True)
        async with database.get_session() as session:
            while True:
                batchsize = self._ctf.get_flag_batchsize()
                ratelimit = self._ctf.get_flag_ratelimit()

                flaglist = []
                resultlist = []
                while len(flaglist) < batchsize:
                    message = await flags.get(fail=False)
                    if message is None:
                        break

                    # TODO: serialize and link to job
                    flag = message.body.decode()
                    print(f"Got flag {flag}")

                    stmt = select(Flag).where(Flag.flag == flag)
                    result = (await session.execute(stmt)).scalars().first()
                    # if there is already such a flag
                    # do not submit, but put in DUPLICATE in database
                    if result is not None:
                        session.add(Flag(flag=flag, status=flag_status.DUPLICATE))
                        await session.commit()
                        message.ack()
                        continue

                    # insert as pending
                    result = Flag(flag=flag, status=flag_status.PENDING)
                    session.add(result)
                    await session.commit()
                    message.ack()

                    flaglist += [flag]
                    resultlist += [result]

                if len(flaglist) > 0:
                    print(f"Submitting {len(flaglist)} flags")
                    statuslist = self._ctf.submit_flags(flaglist)

                    for result, status in zip(resultlist, statuslist):
                        result.status = status
                    await session.commit()

                await asyncio.sleep(ratelimit)
