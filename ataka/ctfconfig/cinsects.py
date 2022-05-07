import logging

from bs4 import BeautifulSoup
from ataka.common.database.models import FlagStatus

import requests

# Config for framework
ROUND_TIME = 60

# format: regex, group where group 0 means the whole regex
FLAG_REGEX = r"FLG\w{30}", 0

FLAG_BATCHSIZE = 100

FLAG_RATELIMIT = 0.5  # Wait in seconds between each call of submit_flags()

START_TIME = 1645280101



LOGIN_URL = "https://dashboard.ctf.cinsects.de/login/?next=/ctf/submit_flag/manual/"
SUBMIT_URL = "https://dashboard.ctf.cinsects.de/ctf/submit_flag/?format=json"
USERNAME = "Cyberwehr"
PASSWORD = "password"




# End config

def get_services():
    return ['securestorage', 'catclub', 'commercial-timetracker', 'hireme', 'deployment_apik', 'deployment_poly', 'hiddenservice8']


def get_targets():
    targets = requests.get("https://dashboard.ctf.cinsects.de/ctf/targets/?format=json")
    obj = targets.json()

    targets = {service: [{"ip": obj[service][team][0], "extra": ""} for team in obj[service]] for service in obj}
    return targets

logger = logging.getLogger()


def submit_flags(flags):
    s = requests.Session()

    r = s.get(LOGIN_URL)

    bs = BeautifulSoup(r.content, 'lxml')
    csrf = bs.find_all("input", {"name": "csrfmiddlewaretoken"})[0]["value"]

    r = s.post(LOGIN_URL, data={"csrfmiddlewaretoken": csrf, "csrfmiddlewaretoken": csrf, "username": USERNAME, "password": PASSWORD, "next": "/ctf/submit_flag/manual/"}, headers={'Content-Type': 'application/x-www-form-urlencoded', "Referer": LOGIN_URL})


    bs = BeautifulSoup(r.content, 'lxml')
    csrf = bs.find_all("input", {"name": "csrfmiddlewaretoken"})[0]["value"]

    r = s.post(SUBMIT_URL, json={"flags": flags}, headers={'Content-Type': 'application/json', "Referer": SUBMIT_URL, "X-Csrftoken": csrf})
    print(r.json())
    
    return [FlagStatus.OK for flag in flags]

