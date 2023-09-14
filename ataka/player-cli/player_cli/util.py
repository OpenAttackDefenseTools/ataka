import os
import time
from datetime import datetime

import player_cli
import requests
import typer
from requests import JSONDecodeError
from rich import print
from rich.text import Text

CHECK_FOR_CMD = re.compile(r'CMD\s+\[\s+(.+)\s+\]')

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
            print(f"{DEBUG_STR}: {method} {endpoint}{'' if params is None else f' with params {params}'}")
            if data is not None:
                print(f"{DEBUG_STR}: {data}")
            print(f"{DEBUG_STR}: ")

        result = player_cli.ctfconfig_wrapper.request(method, endpoint, data=data)
        if player_cli.state['debug']:
            print(f"{DEBUG_STR}: {result}")
        return result

    url = f'http://{player_cli.state["host"]}/api/{endpoint}'

    if player_cli.state['debug']:
        print(f"{DEBUG_STR}: {method} {url}{'' if params is None else f' with params {params}'}")
        if data is not None:
            print(f"{DEBUG_STR}: {data}")
        print(f"{DEBUG_STR}: ")

    func = {
        'GET': requests.get,
        'PUT': requests.put,
        'POST': requests.post,
        'PATCH': requests.patch,
    }[method]
    response = func(url, json=data, params=params)
    if player_cli.state['debug']:
        print(f"{DEBUG_STR}: {response.status_code} {response.reason}")
        print(f"{DEBUG_STR}: {response.json()}")

    if response.status_code != 200:
        print(f"{ERROR_STR}: {method} {endpoint} returned status code {response.status_code} {response.reason}")
        try:
            print(f"{ERROR_STR}: {response.json()}")
        except JSONDecodeError:
            print(f"{ERROR_STR}: {response.text}")
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
    matches = CHECK_FOR_CMD.findall(content)
    if matches:
        ret_arguments = []
        for argument in matches[-1].split(","):
            ret_arguments.append(
                # Partition the string on the first "
                argument.partition("\"")[2]\
                # and on the last "
                .rpartition("\"")[0]
            )

        return ret_arguments
    return None
