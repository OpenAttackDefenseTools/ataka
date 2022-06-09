import logging

from ataka.common.database.models import FlagStatus

import json
import requests
import telnetlib
import socket

# Config for framework
ROUND_TIME = 120

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"SAAR\{[A-Za-z0-9-_]{32}\}", 0

FLAG_BATCHSIZE = 500

FLAG_RATELIMIT = 0.5  # Wait in seconds between each call of submit_flags()

START_TIME = 1653055201 # Fri May 20 2022 4:00:01 PM GMT+02:00 (Central European Summer Time)

# IPs that are always excluded from attacks.
STATIC_EXCLUSIONS = set([])

SUBMIT_DOM = 'submission.ctf.saarland'
SUBMIT_PORT = 31337
FLAGID_URL = 'https://scoreboard.ctf.saarland/attack.json'


def get_services():
    return ["backd00r", "bytewarden", "saarbahn", "saarcloud", "saarloop", "saarsecvv"]


def get_targets():
    try:
        dt = requests.get(FLAGID_URL).json()
        #dt = json.loads('{"teams":[{"id":1,"name":"NOP","ip":"10.32.1.2"},{"id":2,"name":"saarsec","ip":"10.32.2.2"}],"flag_ids":{"service_1":{"10.32.1.2":{"15":["username1","username1.2"],"16":["username2","username2.2"]},"10.32.2.2":{"15":["username3","username3.2"],"16":["username4","username4.2"]}}}}')

        flag_ids = dt['flag_ids']
        teams = dt['teams']
        targets = {
            service: [
                {
                    'ip': ip,
                    'extra': json.dumps([x for tick, flagids in ip_info.items() for x in flagids]),
                }
                for ip, ip_info in service_info.items()
            ]
            for service, service_info in flag_ids.items()
        }

        targets["saarcloud"] = [{"ip": team["ip"], "extra": ""} for team in teams if team["online"]]

        return targets
    except Exception as e:
        print(f"Error while getting targets: {e}")
        return {service: [] for service in get_services()}


def submit_flags(flags):
    results = []
    try:
        conn = telnetlib.Telnet(SUBMIT_DOM, SUBMIT_PORT, 2)

        for flag in flags:
            conn.write((flag + '\n').encode())
            resp = conn.read_until(b"\n").decode()
            if resp == '[OK]\n':
                status = FlagStatus.OK
            elif 'format' in resp:
                status = FlagStatus.FORMAT
            elif 'Invalid flag' in resp:
                status = FlagStatus.INVALID
            elif 'Expired' in resp:
                status = FlagStatus.INACTIVE
            elif 'Already submitted' in resp:
                status = FlagStatus.DUPLICATE
            elif 'NOP team' in resp:
                status = FlagStatus.NOP
            elif 'own flag' in resp:
                status = FlagStatus.OWNFLAG
            elif 'OFFLINE' in resp:
                status = FlagStatus.OFFLINE
            else:
                status = FlagStatus.ERROR
            results.append(status)

        conn.get_socket().shutdown(socket.SHUT_WR)
        conn.read_all()
        conn.close()
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
