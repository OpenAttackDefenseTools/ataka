import sys
import typer

from typing import List, Optional
from player_cli.util import request


app = typer.Typer()


@app.command('submit', help='Submit flags.')
def flag_submit(
    flags: List[str] = typer.Argument(None, help=
        'Flags to submit. '
        'They will be extracted with the flag regex, so they can be dirty. '
        'If no flags are specified, stdin will be read until EOF and submitted.')
):
    if flags:
        data = '\n'.join(flags)
    else:
        data = sys.stdin.read()

    resp_flags = request('POST', 'flag/submit', data={
        'flags': data,
    })

    typer.echo(f'Submitted {len(resp_flags)} flags:')
    for flag in resp_flags:
        typer.echo(flag)
