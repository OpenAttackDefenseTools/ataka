import typer
import player_cli


DEFAULT_HOST = 'ataka.h4xx.eu'


app = typer.Typer()

app.add_typer(player_cli.cmd_exploit.app,
              name='exploit', help='Manage exploits.')
app.add_typer(player_cli.cmd_service.app,
              name='service', help='Manage services.')
app.add_typer(player_cli.cmd_flag.app,
              name='flag', help='Manage flags.')


@app.callback()
def main(
    host: str = typer.Option('ataka.h4xx.eu', '--host', '-h',
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
