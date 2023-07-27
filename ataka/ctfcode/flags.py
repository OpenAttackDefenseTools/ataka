import re
import time
from asyncio import TimeoutError, sleep

import asyncio
from sqlalchemy import update, select

from ataka.common import database
from ataka.common.database.models import Flag
from ataka.common.flag_status import FlagStatus, DuplicatesDontResubmitFlagStatus
from ataka.common.queue import FlagQueue, get_channel, FlagMessage, OutputQueue
from .ctf import CTF


class Flags:
    def __init__(self, ctf: CTF):
        self._ctf = ctf
        self._flag_cache = {}

    async def poll_and_submit_flags(self):
        async with get_channel() as channel:
            flag_queue = await FlagQueue.get(channel)
            last_submit = time.time()

            async with database.get_session() as session:
                while True:
                    batchsize = self._ctf.get_flag_batchsize()
                    ratelimit = self._ctf.get_flag_ratelimit()

                    queue_init = select(Flag).where(Flag.status.in_({FlagStatus.PENDING, FlagStatus.ERROR}))
                    init_list = list((await session.execute(queue_init)).scalars())

                    submit_list = [FlagMessage(flag.id, flag.flag) for flag in init_list if flag.status == FlagStatus.PENDING]
                    resubmit_list = [FlagMessage(flag.id, flag.flag) for flag in init_list if flag.status == FlagStatus.ERROR]
                    dupe_list = []
                    try:
                        async for message in flag_queue.wait_for_messages(timeout=ratelimit):
                            flag_id = message.flag_id
                            flag = message.flag
                            #print(f"Got flag {flag}, cache {'NOPE' if flag not in self._flag_cache else self._flag_cache[flag]}")

                            check_duplicates = select(Flag) \
                                .where(Flag.id != flag_id) \
                                .where(Flag.flag == flag) \
                                .where(Flag.status.in_(DuplicatesDontResubmitFlagStatus)) \
                                .limit(1)
                            duplicate = (await session.execute(check_duplicates)).scalars().first()
                            if duplicate is not None:
                                dupe_list.append(flag_id)
                                self._flag_cache[flag] = FlagStatus.DUPLICATE_NOT_SUBMITTED
                            else:
                                submit_list.append(message)
                                self._flag_cache[flag] = FlagStatus.PENDING

                            if len(submit_list) >= batchsize:
                                break
                    except TimeoutError as e:
                        pass

                    if len(dupe_list) > 0:
                        print(f"Dupe list of size {len(dupe_list)}")
                        set_duplicates = update(Flag)\
                            .where(Flag.id.in_(dupe_list))\
                            .values(status=FlagStatus.DUPLICATE_NOT_SUBMITTED)
                        await session.execute(set_duplicates)
                        await session.commit()

                    if len(submit_list) < batchsize and len(resubmit_list) > 0:
                        resubmit_amount = min(batchsize-len(submit_list), len(resubmit_list))
                        print(f"Got leftover capacity, resubmitting {resubmit_amount} errored flags "
                              f"({len(resubmit_list) - resubmit_amount} remaining)")

                        submit_list += resubmit_list[:resubmit_amount]
                        resubmit_list = resubmit_list[resubmit_amount:]

                    if len(submit_list) > 0:
                        set_pending = update(Flag) \
                            .where(Flag.id.in_([x.flag_id for x in submit_list])) \
                            .values(status=FlagStatus.PENDING) \
                            .returning(Flag)
                        result = list((await session.execute(set_pending)).scalars())
                        await session.commit()

                        diff = time.time() - last_submit
                        print(f"Submitting {len(submit_list)} flags, {diff:.2f}s since last time" +
                              (f" (sleeping {ratelimit-diff:.2f})" if diff < ratelimit else ""))
                        if diff < ratelimit:
                            await sleep(ratelimit-diff)
                        last_submit = time.time()

                        statuslist = self._ctf.submit_flags([flag.flag for flag in result])
                        print(f"Done submitting ({statuslist.count(FlagStatus.OK)} ok)")

                        for flag, status in zip(result, statuslist):
                            #print(flag.id, flag.flag, status)
                            flag.status = status
                            self._flag_cache[flag.flag] = status

                            if status == FlagStatus.ERROR:
                                resubmit_list.append(FlagMessage(flag.id, flag.flag))

                        await session.commit()
                    else:
                        print("No flags for now")

    async def poll_and_parse_output(self):
        async with get_channel() as channel:
            flag_queue = await FlagQueue.get(channel)
            output_queue = await OutputQueue.get(channel)
            async with database.get_session() as session:
                async for message in output_queue.wait_for_messages():
                    regex, group = self._ctf.get_flag_regex()
                    submissions = []
                    duplicates = []
                    for match in re.finditer(regex, message.output):
                        if match.start(group) == -1 or match.end(group) == -1:
                            continue

                        flag = match.group(group)
                        flag_obj = Flag(flag=flag, status=FlagStatus.QUEUED, execution_id=message.execution_id,
                                        stdout=message.stdout, start=match.start(group), end=match.end(group))
                        if flag in self._flag_cache and self._flag_cache[flag] in DuplicatesDontResubmitFlagStatus:
                            flag_obj.status = FlagStatus.DUPLICATE_NOT_SUBMITTED
                            duplicates.append(flag_obj)
                        else:
                            submissions.append(flag_obj)
                            self._flag_cache[flag] = flag_obj.status

                    if len(submissions) + len(duplicates) == 0:
                        continue

                    session.add_all(submissions + duplicates)
                    await session.commit()

                    if len(submissions) > 0:
                        await asyncio.gather(*[
                            flag_queue.send_message(FlagMessage(flag_id=f.id, flag=f.flag))
                            for f in submissions])
