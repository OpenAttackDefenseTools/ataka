import logging
from pwn import *
import requests
import json

# Ataka Host Domain / IP
ATAKA_HOST = 'ataka.h4xx.eu'

# Our own host
OWN_HOST = '10.20.2.'

RUNLOCAL_TARGETS = [
  # NOP Team
  '10.20.1.4',
  '10.20.1.5',
  '10.20.1.6'
]

# Config for framework
ROUND_TIME = 120

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"ICC_[a-zA-Z\/0-9+\-]{32}", 0
#FLAG_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", 0

FLAG_BATCHSIZE = 1000

FLAG_RATELIMIT = 0.5  # Wait in seconds between each call of submit_flags()

# 2023-07-09 09:00:00 GMT
START_TIME = 1688893200

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = set([OWN_HOST + x for x in ["4", "5", "6"]])

# End config


def get_services():
    return ["adorad", "navashield", "flagprescription"]


def flag_ids():
  url = "https://web.ad.teameurope.space/competition/teams.json"

  response = requests.get(url)

  data = None
  try:
      data = response.json()['flag_ids']
  except:
      logger.error(f"Couldn't get flag_ids from {url}")

  return data

  

def get_targets():
    extra = flag_ids()
    #TODO: only show relevant flag_ids
    return {"adorad": [{"ip": f"10.20.{i}.4", "extra": json.dumps([extra['ADorAD - AD'][str(i)], extra['ADorAD - Workhorz'][str(i)]])} for i in range(1,26) if str(i) in extra['ADorAD - AD'] and str(i) in extra["ADorAD - Workhorz"]],
            "navashield": [{"ip": f"10.20.{i}.6", "extra": json.dumps([extra['Navashield - Server'][str(i)], extra['Navashield - Client'][str(i)]])} for i in range(1,26) if str(i) in extra['Navashield - Server'] and str(i) in extra["Navashield - Client"]],
            "flagprescription": [{"ip": f"10.20.{i}.6", "extra": json.dumps([extra['Flag Prescription Prescription'][str(i)], extra['Flag Prescription Appointments'][str(i)]])} for i in range(1,26) if str(i) in extra['Flag Prescription Prescription'] and str(i) in extra["Flag Prescription Appointments"]],
            }
    
    return {service: [{"ip": f"10.20.{i}.{service[1]}", "extra": json.dumps(extra['flag_ids'][service[0]][i]) if not extra is None else None} for i in range(1, 26)] for service in get_services()}


def get_all_target_ips():
    return set([f"10.20.{i}.{j}" for i in range(1, 26) for j in range(4,7)])

"""
    r = requests.get("http://10.10.10.10/api/client/attack_data")

    targets = []
    services = r.json()

    ids = 1
    for (service, ts) in services.items():
        for (target, hints) in ts.items():
            if target == OURSERVER:
                continue
            ta = Target(ip=target, service_id=ids, service_name=service, custom={'extra': json.dumps(hints)})
            targets.append(ta)
        ids += 1

    return targets
"""

logger = logging.getLogger()

"""
SUBMISSION_URL = "10.10.10.100"
SUBMISSION_TOKEN = "30771485d3cb53a3"

RESPONSES = {
    FlagStatus.INACTIVE: ['timeout', 'game not started', 'try again later', 'game over', 'is not up', 'no such flag'],
    FlagStatus.OK: ['accepted', 'congrat'],
    FlagStatus.ERROR: ['bad', 'wrong', 'expired', 'unknown', 'your own', 'too old', 'not in database',
                       'already submitted', 'invalid flag'],
}
"""

HEADER=b"""Play With Team Europe CTF 2023 / Attack-Defense Flag Submission Server
One flag per line please!

"""

def submit_flags(flags):
    results = []
    try:
        server = remote("10.20.151.1", 31111, timeout=2)
        server.recvuntil(HEADER, timeout=10)
        for flag in flags:
            server.sendline(flag.encode())
            response = server.recvline(timeout=5)
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
                logger.error(f"Invalid response: {response}")
    except Exception as e:
        logger.error(f"Exception: {e}")
        results += [FlagStatus.ERROR for _ in flags[len(results)]]

    return results
