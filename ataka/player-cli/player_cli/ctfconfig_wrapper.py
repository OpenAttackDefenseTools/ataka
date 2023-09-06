'''
This file is responsible for mocking some of the API endpoints we have in ataka
    And act as a fallback, in case our tools fail
'''
import re

from .ctfconfig import *

FLAG_FINDER = re.compile(FLAG_REGEX[0])

def init():
    return {
        'ctf_config': {
            'start_time': START_TIME,
            'round_time': ROUND_TIME,
            'flag_regex': FLAG_REGEX,
            'services': get_services()
        },
        'exploits': {
        },
    }


def request(method, endpoint, data=None):
    if endpoint == 'init':
        return init()
    elif endpoint == 'flag/submit':
        return submit_flags(FLAG_FINDER.findall(data['flags']))
    elif endpoint.startswith('targets/service/'):
        return get_targets()[endpoint.split('/')[-1]]
    elif endpoint == 'services':
        return get_services()
    else:
        assert False, f'Invalid request: {method} {endpoint} {data}'
