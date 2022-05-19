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


FLAG_BATCHSIZE = 50

FLAG_RATELIMIT = 0.5  # Wait in seconds between each call of submit_flags()

START_TIME = 1653058800 # Fri May 20 2022 5:00:00 PM GMT+02:00 (Central European Summer Time)

TEAM_TOKEN = ...
SUBMIT_DOM = 'submission.ctf.saarland'
SUBMIT_PORT = 31337
FLAGID_URL = 'https://scoreboard.ctf.saarland/attack.json'


def get_services():
	return []


def get_targets():
	dt = requests.get(FLAGID_URL).json()
	flag_ids = dt['flag_ids'] 
	teams = dt['teams'] 
	targets = {
		service: [
			{
				'ip': ip,
				'extra': json.dumps(ip_info),
			}
			for ip, ip_info in service_info.items()
		]
		for service, service_info in flag_ids.items()
	}

	return targets, teams


def submit_flags(flags):
	conn = telnetlib.Telnet(SUBMIT_DOM, SUBMIT_PORT, 2)
	results = []

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