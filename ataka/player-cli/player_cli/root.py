import typer
import requests
import sys
import player_cli

app = typer.Typer()

app.add_typer(player_cli.cmd_exploit.app,
              name='exploit', help='Manage exploits.')
app.add_typer(player_cli.cmd_service.app,
              name='service', help='Manage services.')
app.add_typer(player_cli.cmd_flag.app,
              name='flag', help='Manage flags.')

@app.callback()
def main(
    host: str = typer.Option(player_cli.ctfconfig_wrapper.ATAKA_HOST, '--host', '-h',
        help='Ataka web API host.'),
    bypass_tools: bool = typer.Option(False, '--bypass-tools', '-b', help=
        'Interact directly with the gameserver instead of using our tools. '
        'Use only in emergencies!')
):
    """
    Player command-line interface to Ataka.
    """
    player_cli.state['host'] = host
    player_cli.state['bypass_tools'] = bypass_tools

@app.command('reload', help='Reload offline ctfconfig')
def reloadConfig():
    cli_path = sys.argv[0]
    resp = requests.get(f"http://{player_cli.state['host']}/")

    if resp.status_code != 200:
        print(f"{player_cli.state['host']} returned {resp.status_code}")
        return

    print(f"Writing player-cli at {cli_path}")
    with open(cli_path, 'wb') as f:
        f.write(resp.content)
