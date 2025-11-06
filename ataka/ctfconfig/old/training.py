import json
import requests

from ataka.common.flag_status import FlagStatus

### EXPORTED CONFIG

# Ataka Host Domain / IP
ATAKA_HOST = "ataka.h4xx.eu"

# Default targets for atk runlocal
RUNLOCAL_TARGETS = [
    # NOP Team
    "10.99.99.1",
]

# IPs that are always excluded from attacks. These can be included in runlocal with --ignore-exclusions
# These still get targets with flag ids, they're just never (automatically) attacked
STATIC_EXCLUSIONS = {
    "TODO: FILL-IN-HERE"
}

ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"shadow\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}", 0

# Maximum list length for submit_flags()
FLAG_BATCHSIZE = 100

# Minimum wait in seconds between each call of submit_flags()
FLAG_RATELIMIT = 1

# When the CTF starts
START_TIME = 1760184000 + 1

### END EXPORTED CONFIG

TEAM_TOKEN = "TODO: FILL-IN-HERE"
SUBMIT_URL = "http://ctf.h4xx.eu/submit"
FLAGID_URL = "http://ctf.h4xx.eu/flagids"

def get_targets():
    try:
        flag_ids = requests.get(FLAGID_URL, timeout=1).json()
        services = set([x for team in flag_ids.values() for x in team.keys()])
        flag_ids = {service: {f"10.99.{i}.1": flag_ids[i][service] if i in flag_ids and service in flag_ids[i] else [] for i in flag_ids.keys()} for service in services}
    except Exception as e:
        print(f"Got error during flagid checking: {e}")
        flag_ids = {}
        services = set()

    services |= {"doeboard"}

    ## A generic solution for just a single vulnbox:
    default_targets = {service: {f"10.99.{i}.1": [] for i in list(range(1,8)) + [99]} for service in services}

    targets = {
        service: [
            {
                "ip": ip,
                "extra": json.dumps(ip_info),
            }
            for ip, ip_info in (default_targets[service] | service_info).items()
        ]
        for service, service_info in ({service: {} for service in services} | flag_ids).items()
    }

    return targets


def submit_flags(flags):
    resp = requests.post(
        SUBMIT_URL, headers={"X-Token": TEAM_TOKEN}, json=flags
    ).json()

    results = []
    for flag in flags:
        if flag not in resp:
            status = FlagStatus.ERROR
            print(f"Error while flag submission: got no response for flag {flag}")
        else:
            msg = resp[flag]
            match msg:
                case "ok":
                    status = FlagStatus.OK
                case "expired":
                    status = FlagStatus.INACTIVE
                case "duplicate":
                    status = FlagStatus.DUPLICATE
                case "ownflag":
                    status = FlagStatus.OWNFLAG
                case "invalid":
                    status = FlagStatus.INVALID
                case _:
                    status = FlagStatus.ERROR
                    print(f"Error while flag submission: {msg}")
        results.append(status)

    return results
