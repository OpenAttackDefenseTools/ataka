import time
from importlib import import_module, reload

from ataka.common.queue import get_channel, ControlQueue, ControlAction, ControlMessage


# A wrapper that loads the specified ctf by name, and wraps the api with support
# for hot-reload and provides a few convenience functions
class CTF:
    def __init__(self, name: str):
        self._module = import_module(f"ataka.ctfconfig.{name}")

    async def watch_for_reload(self):
        async with await get_channel() as channel:
            try:
                control_queue = await ControlQueue.get(channel)

                async for control_message in control_queue.wait_for_messages():
                    match control_message.action:
                        case ControlAction.RELOAD_CONFIG:
                            self.reload()
                            await self._send_ctf_config(control_queue)

                        case ControlAction.GET_CTF_CONFIG:
                            await self._send_ctf_config(control_queue)
            except Exception as e:
                print(e)

    async def _send_ctf_config(self, control_queue):
        return await control_queue.send_message(ControlMessage(action=ControlAction.CTF_CONFIG_UPDATE,
                                                               extra={
                                                                   "start_time": self.get_start_time(),
                                                                   "round_time": self.get_round_time(),
                                                                   "flag_regex": self.get_flag_regex()[0],
                                                                   "services": self.get_services(),
                                                               }))

    def reload(self):
        print("Reloading ctf code")
        reload(self._module)

    def get_round_time(self):
        return self._module.ROUND_TIME

    def get_flag_regex(self):
        return self._module.FLAG_REGEX

    def get_flag_batchsize(self):
        return self._module.FLAG_BATCHSIZE

    def get_flag_ratelimit(self):
        return self._module.FLAG_RATELIMIT

    def get_start_time(self):
        return self._module.START_TIME

    def get_cur_tick(self):
        running_time = time.time() - self.get_start_time()
        return running_time // self.get_round_time()

    def get_next_tick_start(self):
        return self.get_start_time() + self.get_round_time() * (self.get_cur_tick() + 1)

    def get_services(self):
        return self._module.get_services()

    def get_targets(self):
        return self._module.get_targets()

    def submit_flags(self, flags):
        return self._module.submit_flags(flags)
