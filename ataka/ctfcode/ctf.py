from importlib import import_module, reload

from ataka.common.queue import get_channel, ControlQueue, ControlMessage


# A wrapper that loads the specified ctf by name, and wraps the api with support
# for hot-reload.
class CTF:
    def __init__(self, name: str):
        self._module = import_module(f"ataka.ctfconfig.{name}")

    async def watch_for_reload(self):
        async with await get_channel() as channel:
            control = await ControlQueue.get(channel)

            async for control_message in control.wait_for_messages():
                if control_message is ControlMessage.RELOAD_CONFIG:
                    self.reload()

    def reload(self):
        print("Reloading ctf code")
        reload(self._module)

    def get_targets(self):
        return self._module.get_targets()

    def get_round_time(self):
        return self._module.ROUND_TIME

    def get_flag_regex(self):
        return self._module.FLAG_REGEX

    def get_flag_batchsize(self):
        return self._module.FLAG_BATCHSIZE

    def get_flag_ratelimit(self):
        return self._module.FLAG_RATELIMIT

    def submit_flags(self, flags):
        return self._module.submit_flags(flags)
