import logging
from pwn import *
import json
import requests

try:
    from ataka.common.database.models import FlagStatus
except ImportError as e:
    import enum
    class FlagStatus(str, enum.Enum):
        UNKNOWN = 'unknown'

        # everything is fine
        OK = 'ok'

        # Flag is currently being submitted
        QUEUED = 'queued'

        # Flag is currently being submitted
        PENDING = 'pending'

        # We already submitted this flag and the submission system tells us thats
        DUPLICATE = 'duplicate'

        # something is wrong with our submitter
        ERROR = 'error'

        # the service did not check the flag, but told us to fuck off
        RATELIMIT = 'ratelimit'

        # something is wrong with the submission system
        EXCEPTION = 'exception'

        # we tried to submit our own flag and the submission system lets us know
        OWNFLAG = 'ownflag'

        # the flag is not longer active. This is used if a flags are restricted to a
        # specific time frame
        INACTIVE = 'inactive'

        # flag fits the format and could be sent to the submission system, but the
        # submission system told us it is invalid
        INVALID = 'invalid'

        # This status code is used in case the scoring system requires the services to
        # be working. Flags that are rejected might be sent again!
        SERVICEBROKEN = 'servicebroken'

# Ataka Host Domain / IP
ATAKA_HOST = 'ataka.h4xx.eu'

# Our own host
OWN_HOST = '10.10.2.1'

RUNLOCAL_TARGETS = ['10.10.1.1']

# Config for framework
ROUND_TIME = 180

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"ECSC_[A-Za-z0-9\\+/]{32}", 0
#FLAG_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", 0

FLAG_BATCHSIZE = 1000

FLAG_RATELIMIT = 5  # Wait in seconds between each call of submit_flags()

START_TIME = 1663223401 # Thu Sep 15 2022 08:30:01 GMT+0200 (Central European Summer Time)

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = set(['10.10.2.1'])

# End config


def get_services():
    # COPY FROM flagids NOT scoreboard
    return [i for sub in
            [[f"{i}_flagstore1", f"{i}_flagstore2"] for i in 
                ["aquaeductus", "blinkygram", "cantina", "techbay", "winds-of-the-past", "dewaste"]] for i in sub] + ["hps"]


def get_targets():
    #extra = '["1234", "5678"]'
    r = requests.get("http://10.10.254.254/competition/teams.json")

    targets = []
    services = r.json()

    flagids = services['flag_ids']

    return {service: [{"ip": f"10.10.{i}.1", "extra": json.dumps(flagids[service][i])} for i in flagids[service].keys()] if service in flagids else [{"ip": ip, "extra": "[]"} for ip in get_all_target_ips()] for service in get_services()}


def get_all_target_ips():
    return set(f'10.10.{i}.1' for i in range(1, 34))

def submit_flags(flags):
    # TODO for next time: exchange with long-living socket, possibly async API
    results = []
    try: 
        HEADER = b"ECSC 2022 | Attack-Defense Flag Submission Server\nOne flag per line please!\n\n"
        server = remote("10.10.254.254", 31337, timeout=2)
        server.recvuntil(HEADER, timeout=5)
        for flag in flags:
            server.sendline(flag.encode())
            response = server.recvline(timeout=2)
            if b" INV" in response:
               results += [FlagStatus.INVALID]
            elif b' OLD' in response:
                results += [FlagStatus.INACTIVE]
            elif b' OK' in response:
                results += [FlagStatus.OK]
            elif b' OWN' in response:
                results += [FlagStatus.OWNFLAG]
            elif b' DUP' in response:
                results += [FlagStatus.DUPLICATE]
            else:
                results += [FlagStatus.ERROR]
                print(f"Invalid response: {response}")
    except Exception as e:
        print(f"Exception: {e}", flush=True)
        results += [FlagStatus.ERROR for _ in flags[len(results)]]

    return results


if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(get_targets())
    pp.pprint(submit_flags([
        'ECSC_Q1RGLSRZ6/VTRVL7RVEtRB69jI+HvO4m',
        'test_flag_2',
    ]))

