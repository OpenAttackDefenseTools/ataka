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
]

# IPs that are always excluded from attacks. These can be included in runlocal with --ignore-exclusions
# These still get targets with flag ids, they're just never (automatically) attacked
STATIC_EXCLUSIONS = {"10.60.3.1"}

ROUND_TIME = 120

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"[A-Z0-9]{31}=", 0

# Maximum list length for submit_flags()
FLAG_BATCHSIZE = 2500

# Minimum wait in seconds between each call of submit_flags()
FLAG_RATELIMIT = 5

# When the CTF starts
START_TIME = 1728550800 + 1  # Sun Jul 16 2023 09:00:00 GMT+0200 (Central European Summer Time)

### END EXPORTED CONFIG


TEAM_TOKEN = "4a8dbdb0cb17dd0187d119a8afbd1f39"
SUBMIT_URL = "http://10.10.0.1:8080/flags"
FLAGID_URL = "http://10.10.0.1:8081/flagIds"


def get_targets():
    additional_services = ['noflagids']
    
    additional_targets = {service: {str(i): [] for i in range(38)} for service in additional_services}
   
    try:
        flag_ids = requests.get(FLAGID_URL, timeout=1).json()
    except:
        flag_ids = {}
    services = list(flag_ids.keys()) + additional_services
    targets = {
        service: [
            {
                "ip": f'10.60.{team_id}.1',
                "extra": json.dumps(ip_info),
            }
            for team_id, ip_info in service_info.items()
        ]
        for service, service_info in (additional_targets | flag_ids).items()
    }

    return targets


def submit_flags(flags):
    resp = requests.put(
        SUBMIT_URL, headers={"X-Team-Token": TEAM_TOKEN}, json=flags, timeout=1
    ).json()

    results = []
    for flag_resp in resp:
        msg = flag_resp["msg"]
        if flag_resp["status"] == 'ACCEPTED':
            status = FlagStatus.OK
        elif "invalid flag" in msg or "the check which dispatched this flag didn't terminate successfully" in msg:
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
