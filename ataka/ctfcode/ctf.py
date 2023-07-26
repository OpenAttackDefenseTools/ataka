import time
from importlib import import_module, reload
import logging
import traceback
import functools
from subprocess import Popen

import exrex

from ataka.common.flag_status import FlagStatus
from ataka.common.queue import get_channel, ControlQueue, ControlAction, ControlMessage


def catch(default=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error occurred while accessing CTFCode")
                logging.error(traceback.format_exc())
                return default

        return wrapper

    return decorator


def expect(validator=lambda *args, **kwargs: True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if not validator(result, *args, **kwargs):
                logging.error(f"CTF Config returned unexpected result for "
                      f"{func.__name__}({', '.join([repr(x) for x in args] + [str(k) + '=' + repr(v) for k, v in kwargs.items()])})")
                logging.error(result)
            return result

        return wrapper

    return decorator


# A wrapper that loads the specified ctf by name, and wraps the api with support
# for hot-reload and provides a few convenience functions
class CTF:
    def __init__(self, name: str):
        self._name = name
        self._module = import_module(f"ataka.ctfconfig.{name}")
        self._self_test()
        self.package_player_cli()

    def package_player_cli(self):
        logging.info("Packaging player-cli")
        Popen(['/ataka/player-cli/package_player_cli.sh'])

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
                logging.error(traceback.format_exc())

    async def _send_ctf_config(self, control_queue):
        return await control_queue.send_message(ControlMessage(action=ControlAction.CTF_CONFIG_UPDATE,
                                                               extra={
                                                                   "start_time": self.get_start_time(),
                                                                   "round_time": self.get_round_time(),
                                                                   "flag_regex": self.get_flag_regex()[0],
                                                                   "services": self.get_services(),
                                                                   "runlocal_targets": self.get_runlocal_targets(),
                                                               }))

    @catch(default=None)
    def reload(self):
        self.package_player_cli()

        logging.info("Reloading ctf code")
        reload(self._module)
        self._self_test()

    @catch(default=[])
    @expect(validator=lambda x, self: type(x) == list and all([type(s) == str for s in x]))
    def get_runlocal_targets(self):
        return self._module.RUNLOCAL_TARGETS

    @catch(default=set())
    @expect(validator=lambda x, self: type(x) == set and all([type(s) == str for s in x]))
    def get_static_exclusions(self):
        return self._module.STATIC_EXCLUSIONS

    @catch(default=60)
    @expect(validator=lambda x, self: type(x) == int and 0 < x < 14400)
    def get_round_time(self):
        return self._module.ROUND_TIME

    @catch(default=(r".*", 0))
    @expect(validator=lambda x, self: type(x) == tuple and len(x) == 2 and type(x[0]) == str and type(x[1]) == int and
                                      0 <= x[1] < 100)
    def get_flag_regex(self):
        return self._module.FLAG_REGEX

    @catch(default=100)
    @expect(validator=lambda x, self: type(x) == int and 0 < x < 25000)
    def get_flag_batchsize(self):
        return self._module.FLAG_BATCHSIZE

    @catch(default=1)
    @expect(validator=lambda x, self: (type(x) == int or type(x) == float) and 0 < x < self.get_round_time())
    def get_flag_ratelimit(self):
        return self._module.FLAG_RATELIMIT

    @catch(default=1577840400)
    @expect(validator=lambda x, self: type(x) == int and (abs(time.time() - x) // 60 // 60 // 24) < 30)
    def get_start_time(self):
        return self._module.START_TIME

    def get_cur_tick(self):
        running_time = time.time() - self.get_start_time()
        return running_time // self.get_round_time()

    def get_next_tick_start(self):
        return self.get_start_time() + self.get_round_time() * (self.get_cur_tick() + 1)

    @catch(default=[])
    @expect(validator=lambda x, self: type(x) == list and all([type(s) == str for s in x]))
    def get_services(self):
        return self._module.get_services()

    @catch(default={})
    @expect(validator=lambda x, self: type(x) == dict and len(x) == len(self.get_services()) and all(
        [type(x[service]) == list and all(
            ['ip' in entry and 'extra' in entry and type(entry['ip']) == str and type(entry['extra'] == str)
             for entry in x[service]]
        ) for service in self.get_services()]
    ))
    def get_targets(self):
        return self._module.get_targets()

    @catch(default=[])
    @expect(validator=lambda x, self, flags: type(x) == list and len(x) == len(flags) and all(
        [type(status) == FlagStatus for status in x]
    ))
    def submit_flags(self, flags):
        return self._module.submit_flags(flags)

    def _self_test(self):
        logging.info("=" * 40)
        logging.info(f"Running ctf config self test for config {self._name}")
        try:
            self.get_runlocal_targets()
            self.get_static_exclusions()
            self.get_round_time()

            regex, group = self.get_flag_regex()
            batchsize = self.get_flag_batchsize()

            self.get_flag_ratelimit()
            self.get_start_time()

            self.get_services()
            self.get_targets()

            fake_flag_count = min(batchsize, 10)
            logging.info(f"Submitting {fake_flag_count} fake flags...")
            fake_flags = [exrex.getone(regex) for _ in range(fake_flag_count)]
            status_list = self.submit_flags(fake_flags)
            for flag, status in zip(fake_flags, status_list):
                logging.info(f"    {flag} -> {status}")
            logging.info("Test finished (if you only see flag submission results, everything is good)")
        except Exception as e:
            logging.error(f"Self-Test FAILED")
            logging.error(traceback.format_exc())
        logging.info("=" * 40)
