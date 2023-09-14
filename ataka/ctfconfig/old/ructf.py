import logging

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

import json
import requests

# Ataka Host Domain / IP
ATAKA_HOST = 'ataka.h4xx.eu'

# Our own host
OWN_HOST = '10.60.9.3'

RUNLOCAL_TARGETS = [f'10.60.{i}.3' for i in range(2,5)]

# Config for framework
ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"[A-Za-z0-9_]{31}=", 0

FLAG_BATCHSIZE = 100

FLAG_RATELIMIT = 0.5  # Wait in seconds between each call of submit_flags()

START_TIME = 1682143201 #Sat Apr 22 2023 08:00:01 GMT+0200 (Central European Summer Time)

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = set(['10.60.9.3'])

# End config

SERVICES_URL = 'https://monitor.ructf.org/services'
FLAGID_URL = 'https://monitor.ructf.org/flag_ids?service=%s'
SUBMIT_URL = 'https://monitor.ructf.org/flags'

TEAM_TOKEN = 'CLOUD_9_c8a088e09071f040570a229e4a1d12b2'


def get_services():
    # COPY FROM flagids NOT scoreboard
    services = requests.get(SERVICES_URL).json()
    #print(services)
    return [str(service_id) + '_' + str(service_name) for service_id, service_name in services.items()]


def get_targets():
    services = get_services()

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
        return {service: [] for service in get_services()}

def get_all_target_ips():
    return set(f'10.60.{i}.3' for i in range(2, 37))


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


logger = logging.getLogger()


if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(get_targets())
    pp.pprint(submit_flags([
        'test_flag_1',
        'test_flag_2',
    ]))

