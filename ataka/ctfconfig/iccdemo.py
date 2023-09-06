import json
import requests

from ataka.common.flag_status import FlagStatus

### EXPORTED CONFIG

# Ataka Host Domain / IP
ATAKA_HOST = "ataka.h4xx.eu"

# Default targets for atk runlocal
RUNLOCAL_TARGETS = [
    # NOP Team
    "10.60.0.1",
    "10.61.0.1",
    "10.62.0.1",
    "10.63.0.1",
    "10.60.1.1",
    "10.61.1.1",
    "10.62.1.1",
    "10.63.1.1",
    "10.60.7.1",
    "10.61.7.1",
    "10.62.7.1",
    "10.63.7.1",
]

# IPs that are always excluded from attacks. These can be included in runlocal with --ignore-exclusions
# These still get targets with flag ids, they're just never (automatically) attacked
STATIC_EXCLUSIONS = {"10.60.5.1", "10.61.5.1", "10.62.5.1", "10.63.5.1"}

ROUND_TIME = 120

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"[A-Z0-9]{31}=", 0

# Maximum list length for submit_flags()
FLAG_BATCHSIZE = 2500

# Minimum wait in seconds between each call of submit_flags()
FLAG_RATELIMIT = 5

# When the CTF starts
START_TIME = 1689490800 + 1  # Sun Jul 16 2023 09:00:00 GMT+0200 (Central European Summer Time)

### END EXPORTED CONFIG


TEAM_TOKEN = "45f8890e6c13d864527c1e869ca384d0"
SUBMIT_URL = "http://10.10.0.1:8080/flags"
FLAGID_URL = "http://10.10.0.1:8081/flagIds"


def get_services():
    return [
        "CyberUni_1",
        "CyberUni_2",
        "CyberUni_3",
        "CyberUni_4",
        "ClosedSea-1",
        "ClosedSea-2",
        "Trademark",
        "rpn",
    ]


def get_targets():
    ## TODO: fill
    default_targets = {
        "rpn":
            {f"10.60.{i}.1": [] for i in range(10)},
        "CyberUni_1":
            {f"10.61.{i}.1": [] for i in range(10)},
        "CyberUni_2":
            {f"10.61.{i}.1": [] for i in range(10)},
        "Trademark":
            {f"10.62.{i}.1": [] for i in range(10)},
    }
    ## A generic solution for just a single vulnbox:
    # default_targets = {service: {f"10.62.{i}.1": [] for i in range(10)} for service in get_services()}

    flag_ids = requests.get(FLAGID_URL).json()

    targets = {
        service: [
            {
                "ip": ip,
                "extra": json.dumps(ip_info),
            }
            for ip, ip_info in (default_targets[service] | service_info).items()
        ]
        for service, service_info in ({service: [] for service in get_services()} | flag_ids).items()
    }

    return targets


def submit_flags(flags):
    resp = requests.put(
        SUBMIT_URL, headers={"X-Team-Token": TEAM_TOKEN}, json=flags
    ).json()

    results = []
    for flag_resp in resp:
        msg = flag_resp["msg"]
        if flag_resp["status"]:
            status = FlagStatus.OK
        elif "invalid flag" in msg:
            status = FlagStatus.INVALID
        elif "flag from nop team" in msg:
            status = FlagStatus.INACTIVE
        elif "flag is your own" in msg:
            status = FlagStatus.OWNFLAG
        elif "flag too old" in msg or "flag is too old" in msg:
            status = FlagStatus.INACTIVE
        elif "flag already claimed" in msg:
            status = FlagStatus.DUPLICATE
        else:
            status = FlagStatus.ERROR
            print(f"Got error while flagsubmission: {msg}")
        results.append(status)

    return results
