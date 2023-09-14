from rich import print

import typer

from player_cli.exploit.target import get_targets
from player_cli.util import magentify

app = typer.Typer()

@app.command('ls', help='List services (legacy)')
def service_ls():
    targets = get_targets(None)
    services = set([target['service'] for target in targets])

    print(f'Available services:\n' + magentify("\n".join(services)))
