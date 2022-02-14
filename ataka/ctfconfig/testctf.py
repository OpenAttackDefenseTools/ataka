import logging

from ataka.common.database.models import FlagStatus

# Config for framework
ROUND_TIME = 10

FLAG_REGEX = r"[A-Z0-9]{31}="

FLAG_BATCHSIZE = 100

FLAG_RATELIMIT = 0.5  # Wait in seconds between each call of submit_flags()

START_TIME = 1644859882
# End config


def get_services():
    return ["buffalo", "gopher_coin", "kyc", "oly_consensus", "swiss_keys", "to_the_moon", "wall.eth"]


def get_targets():
    return {service: [{"ip": f"10.99.{i}.2", "extra": ""} for i in range(3)] for service in get_services()}


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


def submit_flags(flags):
    return [FlagStatus.OK for flag in flags]


"""
    payload = [flag.flag for flag in flags]
    headers = {'X-Team-Token': SUBMISSION_TOKEN, "Content-Type": "application/json"}
    logger.error("SUBMITTING " + json.dumps(payload))
    r = requests.put("http://" + SUBMISSION_URL + "/flags", data=json.dumps(payload), headers=headers, verify=False,
                     timeout=5)
    logger.error(str(r.status_code) + " " + json.dumps(r.json()))

    return [FlagStatus.OK for flag in flags]

    if r.status_code == 429:
        return FlagStatus.RATELIMIT
    if r.status_code == 200:
        return FlagStatus.OK
        for item in r.json():
            response = item['msg'].strip()
            response = response.replace('[{}] '.format(item['flag']), '')

            response_lower = response.lower()
            for status, substrings in RESPONSES.items():
                if any(s in response_lower for s in substrings):
                    return status

            else:
                return FlagStatus.ERROR

    else:
        logger.error("Exception during flag submission: {} -> {}".format(str(r.status_code), str(r.text)))
        return FlagStatus.ERROR
"""
