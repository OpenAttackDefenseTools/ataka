import typer

from player_cli.util import request


app = typer.Typer()


@app.command('ls', help='List all services.')
def service_ls():
    services = request('GET', 'services')
    for service in services:
        typer.echo(service)
