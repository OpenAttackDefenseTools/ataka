'''
This file is responsible for mocking some of the API endpoints we have in ataka
    And act as a fallback, in case our tools fail
'''
import re

from .ctfconfig import *

FLAG_FINDER = re.compile(FLAG_REGEX[0])

def request(method, endpoint, data=None):
    if endpoint == 'flag/submit':
        # TODO: actually provide working output and implement for runlocal
        return submit_flags(FLAG_FINDER.findall(data['flags']))
    elif endpoint == 'targets':
        return [target | {"service": service} for service,targets in get_targets().items() for target in targets]
    else:
        assert False, f'Invalid request: {method} {endpoint} {data}'
