import json
import requests
    
from pwn import *

from ataka.common.flag_status import FlagStatus

### EXPORTED CONFIG

# Ataka Host Domain / IP
ATAKA_HOST = "ataka.h4xx.eu"

# Default targets for atk runlocal
RUNLOCAL_TARGETS = [
    # NOP Team
    "10.42.1.2",
]

# IPs that are always excluded from attacks. These can be included in runlocal with --ignore-exclusions
# These still get targets with flag ids, they're just never (automatically) attacked
STATIC_EXCLUSIONS = {"10.42.3.2", "10.45.3.2"}

ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"ECSC\{[A-Za-z0-9-_]{32}\}", 0

# Maximum list length for submit_flags()
FLAG_BATCHSIZE = 1000

# Minimum wait in seconds between each call of submit_flags()
FLAG_RATELIMIT = 1

# When the CTF starts
START_TIME = 1759914000 + 1  # Sun Jul 16 2023 09:00:00 GMT+0200 (Central European Summer Time)

### END EXPORTED CONFIG

FLAGID_URL = f"http://10.42.251.2:8080/api/v1/attack_info"

def get_targets():
    no_flagid_services = {"noflagids"}

    flag_ids = {}
    i = 30
    while i > 0:
        try:
            flag_ids = requests.get(FLAGID_URL, timeout=1).json()
            if len(flag_ids.keys()) > 0:
                break
            i -= 1
        except:
            print("Got error while fetching current rounds flag ids")
            import traceback
            print(traceback.format_exc())
            i -= 10

    if len(flag_ids.keys()) == 0:
        default_targets = {service: {i: {"ip": f"10.42.{i}.2", "extra": "[]"} for i in range(1, 40)} for service in no_flagid_services}
    else:
        cur_tick = int(list(sorted(flag_ids.keys()))[-1])

        old_ticks = range(max(1, cur_tick-4), cur_tick)
        for i in old_ticks:
            try:
                flag_ids |= {i: requests.get(FLAGID_URL + f"?round={i}", timeout=1).json()}
            except:
                print("Got error while fetching last rounds flag ids")
                import traceback
                print(traceback.format_exc())

        team_ids = list(set([y for x in flag_ids.values() for y in x.keys()]))
        services = list(set([z for x in flag_ids.values() for y in x.values() for z in y.keys()]))

        ## A generic solution for just a single vulnbox:
        default_targets = {service: {str(i): [] for i in team_ids} for service in no_flagid_services}

        main_ids = {service: {i: [teams[i][service] for teams in flag_ids.values() if i in teams and service in teams[i] and teams[i][service] is not null] for i in team_ids} for service in services}

        flag_ids = main_ids

    targets = {
        service: [
            {
                "ip": f"10.42.{i}.2",
                "extra": json.dumps(info),
            }
            for i, info in (default_targets[service] | service_info).items()
        ]
        for service, service_info in ({service: {} for service in no_flagid_services} | flag_ids).items()
    }

    return targets


def submit_flags(flags):
    print("submitting", len(flags), "flags")
    # TODO for next time: exchange with long-living socket, possibly async API
    results = []
    try:
        #HEADER = b"\nOne flag per line please!\n\n"
        server = remote("10.42.251.2", 1337, timeout=2)
        #server.recvuntil(HEADER, timeout=5)
        server.sendline(b'\n'.join([flag.encode() for flag in flags]))
        i = 0
        buffer = b''
        while i < len(flags):
            buffer += server.recv(timeout=1)
            print('submit fragment', buffer, i, len(flags))
            res = buffer.split(b"\n")
            buffer = res[-1]
            for response in res[:-1]:
                i += 1
                if b"Invalid" in response:
                   results += [FlagStatus.INVALID]
                elif b'Expired' in response:
                    results += [FlagStatus.INACTIVE]
                elif b'OK' in response:
                    results += [FlagStatus.OK]
                elif b'own' in response:
                    results += [FlagStatus.OWNFLAG]
                elif b'Already' in response:
                    results += [FlagStatus.DUPLICATE]
                elif b'NOP' in response:
                    results += [FlagStatus.INVALID]
                else:
                    results += [FlagStatus.ERROR]
                    print(f"Invalid response: {response}")
        server.close()
    except Exception as e:
        print(f"Exception: {e}", flush=True)
        results += [FlagStatus.ERROR for _ in flags[len(results):]]

    return results
