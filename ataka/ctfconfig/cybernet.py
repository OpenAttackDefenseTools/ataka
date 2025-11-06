import json
from pwn import *

from ataka.common.flag_status import FlagStatus

### EXPORTED CONFIG

# Ataka Host Domain / IP
ATAKA_HOST = "10.2.3.27:8000"

# Default targets for atk runlocal
RUNLOCAL_TARGETS = ["10.99.0.2"]

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = {"10.99.1.2"}

ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = {
    "icenet": (r"[A-Z0-9]{32}", 0),
    "geothermal": (r"[0-9]{5,15}", 0),
}
# FLAG_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", 0

FLAG_BATCHSIZE = 100

FLAG_RATELIMIT = 10  # Wait in seconds between each call of submit_flags()

# When the CTF starts
START_TIME = 1762013452

FLAG_SUBMIT_HOST = "10.10.0.4"
FLAG_SUBMIT_PORT = 1337
### END EXPORTED CONFIG


def get_targets():
    teams = [
        {"name": "afduruma", "octet": 7},
        {"name": "langis", "octet": 1},
        {"name": "krongdi", "octet": 6},
        {"name": "zombura", "octet": 8},
        {"name": "elgon", "octet": 4},
        {"name": "xren", "octet": 5},
        {"name": "paradoxan", "octet": 9},
        {"name": "gardari", "octet": 10},
        {"name": "brocktan", "octet": 2},
    ]
    services = [
        # {
        #     "name": "telnet",
        #     "octet": 1
        # },
        {"name": "icenet", "octet": 2},
        {"name": "geothermal", "octet": 2},
    ]

    default_targets = {
        service["name"]: [
            {
                "ip": f"10.1.{team['octet']}.{service['octet']}",
                "extra": "",
            }
            for team in teams
        ]
        for service in services
    }
    return default_targets


submitted_flags = set()


def _randomness():
    import random

    return random.choices(
        [
            FlagStatus.OK,
            FlagStatus.INVALID,
            FlagStatus.INACTIVE,
            FlagStatus.OWNFLAG,
            FlagStatus.ERROR,
        ],
        weights=[0.5, 0.2, 0.2, 0.05, 0.1],
        k=1,
    )[0]


def submit_flags(flags):
    results = []
    context.proxy = (socks.SOCKS5, "172.22.1.2", 1080)
    server = remote(FLAG_SUBMIT_HOST, FLAG_SUBMIT_PORT, timeout=2)
    for flag in flags:
        try:
            server.sendline(flag.encode())
            response = server.recvall(timeout=2)
            if b"OK" in response:
                results += [FlagStatus.OK]
            elif b"INVALID" in response:
                results += [FlagStatus.INVALID]
            else:
                results += [FlagStatus.ERROR]
        except:
            results += [FlagStatus.ERROR]
    server.close()
    return results
