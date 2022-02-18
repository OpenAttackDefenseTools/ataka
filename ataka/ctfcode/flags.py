import re
from asyncio import TimeoutError, sleep

from sqlalchemy.future import select

from ataka.common import database
from ataka.common.database.models import Flag, FlagStatus
from .ctf import CTF
from ..common.queue import FlagQueue, get_channel, FlagMessage
from ..common.queue.output import OutputQueue


class Flags:
    def __init__(self, ctf: CTF):
        self._ctf = ctf

    async def poll_and_submit_flags(self):
        async with await get_channel() as channel:
            flag_queue = await FlagQueue.get(channel)
            async with database.get_session() as session:
                while True:
                    batchsize = self._ctf.get_flag_batchsize()
                    ratelimit = self._ctf.get_flag_ratelimit()

                    submitlist = []
                    try:
                        async for message in flag_queue.wait_for_messages(timeout=ratelimit):
                            flag_id = message.flag_id
                            flag = message.flag
                            print(f"Got flag {flag}")

                            check_duplicates = select(Flag).where(Flag.id != flag_id).where(Flag.flag == flag).limit(1)
                            duplicate = (await session.execute(check_duplicates)).scalars().first()

                            get_flag = select(Flag).where(Flag.id == flag_id)
                            flag_obj = (await session.execute(get_flag)).scalar_one()
                            # if there is already such a flag
                            # do not submit, but put in DUPLICATE in database
                            if duplicate is None:
                                flag_obj.status = FlagStatus.PENDING
                                submitlist += [flag_obj]
                            else:
                                flag_obj.status = FlagStatus.DUPLICATE

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

    async def poll_and_parse_output(self):
        async with await get_channel() as channel:
            flag_queue = await FlagQueue.get(channel)
            output_queue = await OutputQueue.get(channel)
            async with database.get_session() as session:
                async for message in output_queue.wait_for_messages():
                    regex, group = self._ctf.get_flag_regex()
                    flags = []
                    for match in re.finditer(regex, message.output):
                        if match.start(group) is -1 or match.end(group) is -1:
                            continue

                        flags += [Flag(flag=match.group(group), status=FlagStatus.UNKNOWN,
                                       execution_id=message.execution_id if message.manual_id is None else None,
                                       stdout=message.stdout, start=match.start(group), end=match.end(group))]

                    if len(flags) == 0:
                        continue

                    session.add_all(flags)
                    await session.commit()

                    messages = [FlagMessage(flag_id=f.id, flag=f.flag) for f in flags]
                    for message in messages:
                        result = await flag_queue.send_message(message)
