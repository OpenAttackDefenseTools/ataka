import re
import time
from asyncio import sleep, TaskGroup
from typing import NamedTuple
from collections import Counter, defaultdict
from itertools import islice, chain

from sqlalchemy import update, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ataka.common import database
from ataka.common.database.models import Flag
from ataka.common.flag_status import FlagStatus, DuplicatesDontResubmitFlagStatus
from ataka.common.queue import get_channel, OutputQueue
from .ctf import CTF


class FlagInfo(NamedTuple):
    flag_id: int
    flag: str
    status: FlagStatus


class Flags:
    def __init__(self, ctf: CTF):
        self._ctf = ctf
        self._flags_submitted_id: dict[str, int] = {}
        '''
        Each flag string is submitted with one Flag object. This is a cache for the id of this object.
        Specifically, the ID in this dict dictates which Flag object should be submitted for a flag string,
        and block others with the same flag string from being submitted.
        '''

    def _cache_is_duplicate(self, flag_info: FlagInfo) -> bool:
        '''Determines if a flag is a duplicate. May produce false negatives but no false positives.'''
        flag_id, flag, _status = flag_info
        return flag in self._flags_submitted_id and flag_id != self._flags_submitted_id[flag]

    def _cache_set_flag(self, flag_id: int, flag: str, dont_resubmit: bool):
        match (flag in self._flags_submitted_id, dont_resubmit):
            case (False, True):
                # This flag blocks resubmission
                self._flags_submitted_id[flag] = flag_id
            case (True, False) if flag_id == self._flags_submitted_id[flag]:
                # This flag used to block resubmission but does not anymore
                self._flags_submitted_id.pop(flag)

    async def set_flags_status(
        self,
        session: AsyncSession,
        flag_infos: list[FlagInfo],
        status: FlagStatus
    ):
        '''
        Use `session` to set the status of all flags in `flag_infos` to `status`.
        '''
        if len(flag_infos) == 0:
            print(f'No flags to mark as {status}')
            return
        flag_ids, _, statuses = zip(*flag_infos)
        status_counted = Counter(statuses)
        prev_status_str = ', '.join(f'{status.name}: {count}' for status, count in status_counted.items())
        print(f'Marking {len(flag_infos)} flags as {status}, original statuses: {prev_status_str}')

        for flag_id, flag, _status in flag_infos:
            self._cache_set_flag(flag_id, flag, status in DuplicatesDontResubmitFlagStatus)
        # Postgres has a limit of 32k parameters in prepared statements, including `IN (?, ?, ?, ... )`
        iterator = iter(flag_ids)
        while batch := tuple(islice(iterator, 30_000)):
            set_status = update(Flag) \
                .where(Flag.id.in_(batch)) \
                .values(status=status)
            await session.execute(set_status)

    async def poll_and_submit_flags(self):
        last_submit = time.time()

        async with database.get_session() as session:
            while True:
                batchsize = self._ctf.get_flag_batchsize()
                ratelimit = self._ctf.get_flag_ratelimit()

                flag_status_priorities = [FlagStatus.PENDING, FlagStatus.QUEUED, FlagStatus.ERROR]

                # Collect potentially submittable flags
                flag_infos_query = select(Flag.id, Flag.flag, Flag.status) \
                    .where(Flag.status.in_(flag_status_priorities))
                flag_infos = map(lambda tuple : FlagInfo(*tuple), (await session.execute(flag_infos_query)).fetchall())
                flag_infos_by_status = defaultdict[str, list[FlagInfo]](list)
                for flag_info in flag_infos:
                    flag_infos_by_status[flag_info.status].append(flag_info)
                flag_infos_prioritized = chain(*(flag_infos_by_status[status] for status in flag_status_priorities))
                del flag_infos_query, flag_infos, flag_infos_by_status

                # Deduplicate QUEUED flags
                duplicates: list[FlagInfo] = []
                maybe_duplicates: list[FlagInfo] = []
                non_duplicates: list[FlagInfo] = []

                # # Find potentially duplicate flags
                for flag_info in flag_infos_prioritized:
                    if flag_info.status == FlagStatus.QUEUED:
                        if self._cache_is_duplicate(flag_info):
                            duplicates.append(flag_info)
                        else:
                            maybe_duplicates.append(flag_info)
                    else:
                        non_duplicates.append(flag_info)
                del flag_infos_prioritized

                # # Fill cache
                if len(maybe_duplicates) > 0:
                    flags = set(flag_info.flag for flag_info in maybe_duplicates)
                    iterator = iter(flags)
                    while batch := list(islice(iterator, 30_000)):
                        dont_resubmit_flags_query = select(func.min(Flag.id), Flag.flag) \
                            .where(Flag.flag.in_(batch)) \
                            .where(Flag.status.in_(DuplicatesDontResubmitFlagStatus)) \
                            .group_by(Flag.flag)
                        dont_resubmit_flags = (await session.execute(dont_resubmit_flags_query)).all()
                        for flag_id, flag_info in dont_resubmit_flags:
                            self._cache_set_flag(flag_id, flag_info, True)

                # # Mark duplicates using the new cache
                for flag_info in maybe_duplicates:
                    if self._cache_is_duplicate(flag_info):
                        duplicates.append(flag_info)
                    else:
                        non_duplicates.append(flag_info)

                if len(duplicates):
                    await self.set_flags_status(session, duplicates, FlagStatus.DUPLICATE_NOT_SUBMITTED)
                await session.commit()

                # Take first max. batchsize flags
                flag_infos_to_submit = non_duplicates[:batchsize]

                del non_duplicates, maybe_duplicates, duplicates
                # Submit flags
                if len(flag_infos_to_submit):
                    await self.set_flags_status(session, flag_infos_to_submit, FlagStatus.PENDING)

                    diff = time.time() - last_submit
                    print(f"Prepared {len(flag_infos_to_submit)} flags for submission, {diff:.2f}s since last time" +
                          (f" (sleeping {ratelimit-diff:.2f})" if diff < ratelimit else ""))
                    if diff < ratelimit:
                        await sleep(ratelimit-diff)
                    last_submit = time.time()

                    statuslist = self._ctf.submit_flags([flag_info.flag for flag_info in flag_infos_to_submit])
                    print(f"Done submitting ({statuslist.count(FlagStatus.OK)} ok)")

                    flag_infos_by_status = defaultdict[str, list[FlagInfo]](list)
                    for flag_info, status in zip(flag_infos_to_submit, statuslist):
                        flag_infos_by_status[status].append(flag_info)

                    async with TaskGroup() as tg:
                        for status, flag_infos in flag_infos_by_status.items():
                            tg.create_task(self.set_flags_status(session, flag_infos, status))
                    await session.commit()
                else:
                    print("No flags for now")
                    await sleep(ratelimit)
                del flag_infos_to_submit

    async def poll_and_parse_output(self):
        async with get_channel() as channel:
            output_queue = await OutputQueue.get(channel)
            async with database.get_session() as session:
                async for message in output_queue.wait_for_messages():
                    regex, group = self._ctf.get_flag_regex()
                    flags_objs = []
                    for match in re.finditer(regex, message.output):
                        if match.start(group) == -1 or match.end(group) == -1:
                            continue

                        flag = match.group(group)
                        flag_obj = Flag(flag=flag, status=FlagStatus.QUEUED, execution_id=message.execution_id,
                                        stdout=message.stdout, start=match.start(group), end=match.end(group))
                        if self._cache_is_duplicate((flag_obj.id,  flag_obj.flag, flag_obj.status)):
                            flag_obj.status = FlagStatus.DUPLICATE_NOT_SUBMITTED
                        flags_objs.append(flag_obj)

                    if len(flags_objs) == 0:
                        continue

                    session.add_all(flags_objs)
                    await session.commit()
                    del flag_obj, flags_objs
