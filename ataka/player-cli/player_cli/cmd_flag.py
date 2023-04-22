import sys
import typer

from typing import List, Optional
from player_cli.util import request, ERROR_STR, magentify, greenify, blueify

from player_cli.ctfconfig_wrapper import OWN_HOST, RUNLOCAL_TARGETS


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

@app.command("ids", help="Print flagids")
def flag_ids(
        service: str = typer.Argument(..., help='Service ID'),
        target_ips: List[str] = typer.Option(RUNLOCAL_TARGETS, '--target', '-T', help=
            'Which Targets to print flag ids (you can specify this option multiple times).'),
        no_target_ips: List[str] = typer.Option([], '-N', '--no-target', help=
            'Which Targets to exclude (you can specify this option multiple times).'),
        all_targets: bool = typer.Option(False, '--all-targets', help=
            'All targets (overrides --target).'),
        exclude_own: bool = typer.Option(False, help=
            'Exclude our own vulnbox from the flagids.'),
        ):

    target_ips = set(target_ips)
    no_target_ips = set(no_target_ips)

    config = request('GET', 'init')
    if config['ctf_config'] is None:
        typer.echo(f'{ERROR_STR}: no CTF config from backend')
        raise typer.Exit(code=1)
    ctf_config = config['ctf_config']

    services = ctf_config['services']
    if service not in services:
        typer.echo(
            f'{ERROR_STR}: unknown service "{service}". '
            f'Available services: {magentify(", ".join(services))}.')
        raise typer.Exit(code=1)

    targets = request('GET', f'targets/service/{service}')
    if not all_targets:
        targets = [t for t in targets if t['ip'] in target_ips]
    if exclude_own:
        targets = [t for t in targets if t['ip'] != OWN_HOST]
    targets = [t for t in targets if t['ip'] not in no_target_ips]

    targets_summary = ', '.join(t['ip'] for t in targets)
    typer.echo(f'[*] Flag IDs for service {greenify(service)}')
    for t in targets:
        typer.echo(f'{blueify(t["ip"])} => {t["extra"]}')

