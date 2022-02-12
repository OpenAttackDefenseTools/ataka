from importlib import import_module, reload


# A wrapper that loads the specified ctf by name, and wraps the api with support
# for hot-reload.
class CTF:
    def __init__(self, name: str):
        self._module = import_module(f"ataka.ctfconfig.{name}")

    def reload(self):
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
