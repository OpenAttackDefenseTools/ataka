import os
import time
from datetime import datetime

import player_cli
import requests
import typer

CHECK_FOR_CMD = re.compile(r'CMD\s?\[\s?(.+)\s?\]')
EXTRACT_CMD = re.compile(r'"([\w.]+)"')

def colorfy(msg, color):
    return typer.style(msg, fg=color, bold=True)


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


ERROR_STR = redify('ERROR')
WARN_STR = yellowfy('WARNING')
NOTICE_STR = blueify('NOTICE')


def request(method, endpoint, data=None, params=None):
    if player_cli.state['bypass_tools']:
        return player_cli.ctfconfig_wrapper.request(method, endpoint, data=data)

    url = f'http://{player_cli.state["host"]}/api/{endpoint}'
    func = {
        'GET': requests.get,
        'PUT': requests.put,
        'POST': requests.post,
        'PATCH': requests.patch,
    }[method]
    return func(url, json=data, params=params).json()


def check_response(resp):
    if 'success' not in resp:
        typer.echo(f'{ERROR_STR}: invalid API response: {resp}')
        raise typer.Exit(code=1)
    if not resp['success']:
        error = resp.get('error', '???')
        typer.echo(f'{ERROR_STR}: API error: {error}')
        raise typer.Exit(code=1)


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
        return EXTRACT_CMD.findall(matches[0])
    return None
