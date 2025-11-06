from pwn import *
import json
import requests

try:
    from ataka.common.database.models import FlagStatus
except ImportError as e:
    import enum

    class FlagStatus(str, enum.Enum):
        UNKNOWN = "unknown"

        # everything is fine
        OK = "ok"

        # Flag is currently being submitted
        QUEUED = "queued"

        # Flag is currently being submitted
        PENDING = "pending"

        # We already submitted this flag and the submission system tells us thats
        DUPLICATE = "duplicate"

        # something is wrong with our submitter
        ERROR = "error"

        # the service did not check the flag, but told us to fuck off
        RATELIMIT = "ratelimit"

        # something is wrong with the submission system
        EXCEPTION = "exception"

        # we tried to submit our own flag and the submission system lets us know
        OWNFLAG = "ownflag"

        # the flag is not longer active. This is used if a flags are restricted to a
        # specific time frame
        INACTIVE = "inactive"

        # flag fits the format and could be sent to the submission system, but the
        # submission system told us it is invalid
        INVALID = "invalid"

        # This status code is used in case the scoring system requires the services to
        # be working. Flags that are rejected might be sent again!
        SERVICEBROKEN = "servicebroken"


FLAG_SUBMIT_HOST = "10.0.13.37"
FLAG_SUBMIT_PORT = 1337

# Ataka Host Domain / IP
ATAKA_HOST = "ataka.local"

# Our own host
OWN_HOST = "10.1.2.1"

RUNLOCAL_TARGETS = ["10.1.1.1"]

# Config for framework
ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"ENO[A-Za-z0-9+\/=]{48}", 0


FLAG_BATCHSIZE = 1000

FLAG_RATELIMIT = 5  # Wait in seconds between each call of submit_flags()

START_TIME = 1690027200

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = set(["10.1.2.1"])

# End config


def get_services() -> list:
    return [
        "asocialnetwork",
        "bollwerk",
        "phreaking",
        "yvm",
        "granulizer",
        "oldschool",
        "steinsgate",
    ]


def get_targets() -> dict:
    r = requests.get(f"https://7.enowars.com/scoreboard/attack.json")

    services = r.json()["services"]
    print("getting services")
    return {
        service: [
            {"ip": ip, "extra": json.dumps(services[service][ip])}
            for ip in services[service].keys()
        ]
        if service in services
        else [{"ip": ip, "extra": "[]"} for ip in get_all_target_ips()]
        for service in get_services()
    }


def get_all_target_ips() -> set:
    r = requests.get(f"https://7.enowars.com/api/data/ips")
    ips = r.text.split("\n")
    ips = [ip for ip in ips if ip != ""]
    return set(ips)


def submit_flags(flags) -> list:
    # TODO for next time: exchange with long-living socket, possibly async API
    results = []
    try:
        HEADER = b"Welcome to the EnoEngine's EnoFlagSink\xe2\x84\xa2!\nPlease submit one flag per line. Responses are NOT guaranteed to be in chronological order.\n\n"
        server = remote(FLAG_SUBMIT_HOST, FLAG_SUBMIT_PORT, timeout=2)
        server.recvuntil(HEADER, timeout=5)
        for flag in flags:
            server.sendline(flag.encode())
            response = server.recvline(timeout=2)
            if b" INV" in response:
                results += [FlagStatus.INVALID]
            elif b" OLD" in response:
                results += [FlagStatus.INACTIVE]
            elif b" OK" in response:
                results += [FlagStatus.OK]
            elif b" OWN" in response:
                results += [FlagStatus.OWNFLAG]
            elif b" DUP" in response:
                results += [FlagStatus.DUPLICATE]
            else:
                results += [FlagStatus.ERROR]
                print(f"Invalid response: {response}")
        server.close()
    except Exception as e:
        print(f"Exception: {e}", flush=True)
        results += [FlagStatus.ERROR for _ in flags[len(results)]]

    return results


if __name__ == "__main__":
    import pprint

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(get_targets())
    pp.pprint(
        submit_flags(
            [
                "ENOBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "ENOBCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "jou",
            ]
        )
    )
