import json

from ataka.common.flag_status import FlagStatus

### EXPORTED CONFIG

# Ataka Host Domain / IP
ATAKA_HOST = 'ataka.h4xx.eu'

# Default targets for atk runlocal
RUNLOCAL_TARGETS = ["10.60.1.3"]

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = {'10.61.84.3'}

ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"[A-Z0-9]{31}=", 0
# FLAG_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", 0

FLAG_BATCHSIZE = 100

FLAG_RATELIMIT = 1  # Wait in seconds between each call of submit_flags()

# When the CTF starts
START_TIME = 1699092000

### END EXPORTED CONFIG

import requests

SERVICES_URL = 'https://monitor.cloud.ructf.org/services'
FLAGID_URL = 'https://monitor.cloud.ructf.org/flag_ids?service=%s'
SUBMIT_URL = 'https://monitor.cloud.ructf.org/flags'

TEAM_TOKEN = 'CLOUD_340_d86dc72998b6f974679d5c963a79a5cc'

def get_targets():
    # COPY FROM flagids NOT scoreboard
    services = requests.get(SERVICES_URL).json()
    #print(services)
    services = [str(service_id) + '_' + str(service_name) for service_id, service_name in services.items()]

    try:
        targets = {}

        for service_name in services:
            service_id = service_name.split('_', 1)[0]
            dt = requests.get(FLAGID_URL % (service_id,), headers={"X-Team-Token": TEAM_TOKEN}).json()
            # print(dt)

            flag_ids = dt['flag_ids']
            targets[service_name] = [
                {
                    'ip': data['host'],
                    'extra': json.dumps(data['flag_ids'])
                }
                for team_id, data in flag_ids.items()
            ]
        #print(targets)
        return targets
    except Exception as e:
        print(f"Error while getting targets: {e}")
        return {service: [] for service in services}


    services = ["buffalo", "gopher_coin", "kyc", "oly_consensus", "swiss_keys", "to_the_moon", "wall.eth"]

    default_targets = {service: {f"10.99.{i}.2": ["1234", "5678"] for i in range(10)} for service in services}

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

def submit_flags(flags):
    results = []
    try:
        conn = requests.put(SUBMIT_URL, json=flags, headers={'X-Team-Token': TEAM_TOKEN})
        resp = conn.json()
        for flag_answer in resp:
            msg = flag_answer["msg"]
            if 'Accepted' in msg:
                status = FlagStatus.OK
            elif 'invalid or own flag' in msg:
                status = FlagStatus.INVALID
            elif 'flag is too old' in resp:
                status = FlagStatus.INACTIVE
            elif 'already submitted' in msg:
                status = FlagStatus.DUPLICATE
            # elif 'NOP team' in resp:
            #     status = FlagStatus.NOP
            #elif 'flag is your own' in msg:
            #    status = FlagStatus.OWNFLAG
            # elif 'OFFLINE' in resp:
            #     status = FlagStatus.OFFLINE
            else:
                status = FlagStatus.ERROR
                print(msg)
            results.append(status)

    except Exception as e:
        print(f"Error while submitting flags: {e}")
        results += [FlagStatus.ERROR]*(len(flags)-len(results))

    return results

