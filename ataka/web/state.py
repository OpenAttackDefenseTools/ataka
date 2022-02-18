import asyncio

from sqlalchemy import select

from ataka.common.database import get_session
from ataka.common.database.models import Exploit
from ataka.common.queue import FlagNotifyQueue, ControlQueue, ControlAction, ControlMessage, get_channel, ExploitQueue


class GlobalState:
    global_channel = None
    flag_notify_queue: FlagNotifyQueue = None
    control_queue: ControlQueue = None
    exploit_queue: ExploitQueue = None

    ctf_config_task = None
    exploit_task = None

    ctf_config = None
    exploits = {}

    @classmethod
    async def get(cls):
        self = cls()

        self.global_channel = await get_channel()
        self.flag_notify_queue = await FlagNotifyQueue.get(self.global_channel)
        self.control_queue = await ControlQueue.get(self.global_channel)
        self.exploit_queue = await ExploitQueue.get(self.global_channel)

        self.ctf_config_task = asyncio.create_task(self.listen_for_ctf_config())
        self.exploit_task = asyncio.create_task(self.listen_for_exploits())

        return self

    async def listen_for_ctf_config(self):
        async def wait_for_updates():
            async for message in self.control_queue.wait_for_messages():
                match message.action:
                    case ControlAction.CTF_CONFIG_UPDATE:
                        self.ctf_config = message.extra
                        print("Reloaded config")

        async def ask_for_updates_repeated():
            while self.ctf_config is None:
                await self.control_queue.send_message(ControlMessage(action=ControlAction.GET_CTF_CONFIG))
                await asyncio.sleep(0.5)

        await asyncio.gather(wait_for_updates(), ask_for_updates_repeated())

    async def listen_for_exploits(self):
        async for message in self.exploit_queue.wait_for_messages():
            async with get_session() as session:
                get_exploit = select(Exploit).where(Exploit.id == message.exploit_id)
                exploit = (await session.execute(get_exploit)).scalars().first()

            self.exploits[exploit.id] = exploit
            print("exploit change", message)

    async def close(self):
        await asyncio.wait_for(self.ctf_config_task, 0.1)
        await asyncio.wait_for(self.exploit_task, 0.1)

        await self.global_channel.close()
