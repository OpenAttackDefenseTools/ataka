import os
import re
import time
from datetime import datetime

import player_cli
import requests
import typer
from requests import JSONDecodeError
from rich import print
from rich.text import Text
from rich.markup import escape


CHECK_FOR_CMD = re.compile(r'CMD\s*\[\s*(.+)\s*\]')


def colorfy(msg, color):
    return f'[bold {color}]{msg}[/bold {color}]'


def magentify(msg):
    return colorfy(msg, typer.colors.MAGENTA)


def blueify(msg):
    return colorfy(msg, typer.colors.BLUE)


def greenify(msg):
    return colorfy(msg, typer.colors.GREEN)


def redify(msg):
    return colorfy(msg, typer.colors.RED)


def yellowfy(msg):
    return colorfy(msg, typer.colors.YELLOW)


DEBUG_STR = colorfy('DEBUG', 'bright_yellow')
ERROR_STR = redify('ERROR')
WARN_STR = yellowfy('WARNING')
NOTICE_STR = blueify('NOTICE')


def request(method, endpoint, data=None, params=None):
    if player_cli.state['bypass_tools']:
        if player_cli.state['debug']:
            print(f"{DEBUG_STR}: {yellowfy('BYPASS')} " + escape(f"{method} {endpoint}{'' if params is None else f' with params {params}'}"))
            if data is not None:
                print(f"{DEBUG_STR}: {yellowfy('BYPASS')} " + escape(data))
            print(f"{DEBUG_STR}: ")

        result = player_cli.ctfconfig_wrapper.request(method, endpoint, data=data)
        if player_cli.state['debug']:
            print(f"{DEBUG_STR}: {yellowfy('BYPASS')} " + escape(result))
        return result

    url = f'http://{player_cli.state["host"]}/api/{endpoint}'

    if player_cli.state['debug']:
        print(f"{DEBUG_STR}: " + escape(f"{method} {url}{'' if params is None else f' with params {params}'}"))
        if data is not None:
            print(f"{DEBUG_STR}: " + escape(data))
        print(f"{DEBUG_STR}: ")

    func = {
        'GET': requests.get,
        'PUT': requests.put,
        'POST': requests.post,
        'PATCH': requests.patch,
    }[method]
    response = func(url, json=data, params=params)
    if player_cli.state['debug']:
        print(f"{DEBUG_STR}: " + escape(f"{response.status_code} {response.reason}"))
        print(f"{DEBUG_STR}: " + escape(response.json()))

    if response.status_code != 200:
        print(f"{ERROR_STR}: " + escape(f"{method} {endpoint} returned status code {response.status_code} {response.reason}"))
        try:
            print(f"{ERROR_STR}: " + escape(response.json()))
        except JSONDecodeError:
            print(f"{ERROR_STR}: " + escape(response.text))
        raise typer.Exit(code=1)
    return response.json()


def dt_from_iso(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f%z')


def dt_to_local_str(dt):
    # This can break in rare cases, but it's mostly fine.
    # It avoids depending on dateutil.
    epoch = time.mktime(dt.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    local_dt = dt + offset
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')


def make_executable(path):
    mode = os.stat(path).st_mode
    # copy R bits to X
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


def highlight_flags(s, func):
    repl = lambda m: func(m.group(0))
    return player_cli.ctfconfig_wrapper.FLAG_FINDER.sub(repl, s)


def parse_dockerfile_cmd(content: str) -> list[str] | None:
    """ Extractes the CMD-Block out of a dockerfile and parses it

    Args:
        content (str): The content of the dockerfile

    Returns:
        list[str] | None: Either a list containing the programm and 
                          the arguments, in a special uecase an empty list
                          (see examples) or None

    Usage examples:
    >>> parse_dockerfile_cmd('CMD [ "prog"]')
    ['prog']
    >>> parse_dockerfile_cmd("CMD [ 'prog','arg1']")
    ['prog', 'arg1']
    >>> parse_dockerfile_cmd('CMD [ "prog", \\'arg1\\']')
    ['prog', 'arg1']
    >>> parse_dockerfile_cmd("CMD [ \\"prog\\", 'arg1']")
    ['prog', 'arg1']
    >>> parse_dockerfile_cmd('CMD []') is None
    True
    >>> parse_dockerfile_cmd('CMD [ ]') # In this case, a empty list is returned
    []
    """
    matches = CHECK_FOR_CMD.findall(content)
    if matches:
        ret_arguments = []
        for argument in matches[-1].split(","):
            argument = argument.strip()
            # If the length is zero, don't add an empty string
            if len(argument) == 0:
                continue

            ret_arguments.append(
                argument[1:-1]
            )

        return ret_arguments
    return None
