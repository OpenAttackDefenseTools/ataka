import json

from ataka.common.flag_status import FlagStatus

### EXPORTED CONFIG

# Ataka Host Domain / IP
ATAKA_HOST = 'localhost:8000'

# Default targets for atk runlocal
RUNLOCAL_TARGETS = ["10.99.0.2"]

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = set([])

ROUND_TIME = 10

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"[A-Z0-9]{31}=", 0
# FLAG_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", 0

FLAG_BATCHSIZE = 100

FLAG_RATELIMIT = 1  # Wait in seconds between each call of submit_flags()

# When the CTF starts
START_TIME = 1690227547


### END EXPORTED CONFIG


def get_services():
    return ["buffalo", "gopher_coin", "kyc", "oly_consensus", "swiss_keys", "to_the_moon", "wall.eth"]


def get_targets():
    services = get_services()

    default_targets = {service: {f"10.99.{i}.2": ["1234", "5678"] for i in range(3)} for service in services}

    # remote fetch here
    flag_ids = default_targets

    targets = {
        service: [
            {
                "ip": ip,
                "extra": json.dumps(ip_info),
            }
            for ip, ip_info in (default_targets[service] | service_info).items()
        ]
        for service, service_info in ({service: [] for service in services} | flag_ids).items()
    }

    return targets


submitted_flags = set()


def _randomness():
    import random
    return \
        random.choices([FlagStatus.OK, FlagStatus.INVALID, FlagStatus.INACTIVE, FlagStatus.OWNFLAG, FlagStatus.ERROR],
                       weights=[0.5, 0.2, 0.2, 0.05, 0.1], k=1)[0]


def submit_flags(flags):
    import time
    time.sleep(min(len(flags) / 1000, 2))
    result = {flag: FlagStatus.DUPLICATE if flag in submitted_flags else _randomness() for flag in flags}
    submitted_flags.update([flag for flag, status in result.items() if status != FlagStatus.ERROR])
    return [result[flag] for flag in flags]
