'''
This file is responsible for mocking some of the API endpoints we have in ataka
    And act as a fallback, in case our tools fail
'''
from rich import print
import re

from .ctfconfig import *

FLAG_FINDER = re.compile(FLAG_REGEX[0])

def _parse_and_submit_content(data: str):
    from player_cli.flags import FLAG_STATUS_COLOR

    flags = list(set(FLAG_FINDER.findall(data)))

    # TODO: no ratelimit, but batch runs
    submissions = submit_flags(flags)

    for flag, status in zip(flags, submissions):
        print(f"{flag} -> {FLAG_STATUS_COLOR[status](status)}")

def request(method, endpoint, data=None):
    if endpoint == 'flag/submit':
        _parse_and_submit_content(data['flags'])
        return {"execution_id": 0}
    elif endpoint == 'targets':
        return [target | {"service": service, "id": i} for service, targets in get_targets().items() for i, target in zip(range(100000), targets)]
    elif endpoint == "job":
        # create fake job
        return {'executions': [{'target_id': x, 'id': 0, 'status': "running"} for x in data['targets']], 'id': 0}
    elif endpoint == "flag/execution/0":
        return []
    elif endpoint == "job/execution/0/finish":
        # submit data
        _parse_and_submit_content(data['stdout'])
        _parse_and_submit_content(data['stderr'])
        return {}
    elif endpoint == "job/0/finish":
        # finish job
        pass
    else:
        assert False, f'Invalid request: {method} {endpoint} {data}'
