import sys
import time
from typing import List, Optional
from rich.live import Live
from rich.table import Table
from rich import print, box

import typer

from player_cli.ctfconfig_wrapper import RUNLOCAL_TARGETS
from player_cli.exploit import get_targets
from player_cli.util import request, ERROR_STR, magentify, greenify, blueify, redify, yellowfy

app = typer.Typer(no_args_is_help=True)

FLAG_STATUS_IS_FINAL = {'ok', 'duplicate', 'duplicate_not_submitted', 'nop', 'ownflag', 'inactive', 'invalid'}

FLAG_STATUS_COLOR = {
    'ok': greenify,
    'queued': blueify,
    'pending': blueify,
    'duplicate': lambda x: x,
    'duplicate_not_submitted': lambda x: x,
    'unknown': redify,
    'error': redify,
    'nop': yellowfy,
    'ownflag': yellowfy,
    'inactive': lambda x: x,
    'invalid': lambda x: x,
}

def generate_summary(flags) -> Table:
    table = Table(box=box.ROUNDED)

    categories = sorted(set([flag['status'] for flag in flags]))
    summary = {category: len([flag for flag in flags if flag['status'] == category]) for category
               in categories}

    for category in summary.keys():
        table.add_column(FLAG_STATUS_COLOR[category](category))

    table.add_row(*[str(count) for count in summary.values()])
    return table

def generate_flag_status_table(flags) -> Table:
    has_targets = any(['target' in flag for flag in flags])

    table = Table(box=box.ROUNDED)
    # Print details
    table.add_column("ID")
    table.add_column("FLAG (duplicates hidden)")
    if has_targets:
        table.add_column("TARGET")
    table.add_column("STATUS")

    for flag in sorted(flags, key=lambda x: x['id']):
        # filter dupes
        if flag['status'] != 'duplicate_not_submitted':
            status_line = ' -> '.join([FLAG_STATUS_COLOR[s](s) for s in flag['status_list']])
            if has_targets:
                table.add_row(str(flag['id']), flag['flag'], flag['target']['ip'], status_line)
            else:
                table.add_row(str(flag['id']), flag['flag'], status_line)

    return table


def poll_and_show_flags(executions: int | list[int], force_detail=False, timeout=10, pollrate=0.5):
    if type(executions) == int:
        executions = [executions]

    flags = [flag for execution_id in executions for flag in request('GET', f'flag/execution/{execution_id}')]
    if len(flags) == 0:
        print("No flags found.")
        return

    flag_count = len(flags)
    intro = f'Submitted {flag_count} flags:'
    print(intro)

    old_flags = {flag['id']: flag | {"status_list": [flag['status']]} for flag in flags}

    finished_flags = {flag['id']: flag for flag in flags if flag['status'] in FLAG_STATUS_IS_FINAL}

    if len([x for x in old_flags.values() if x['status'] != 'duplicate_not_submitted']) > 20 and not force_detail:
        show_detail = False
        table_generator = generate_summary
    else:
        show_detail = True
        table_generator = generate_flag_status_table

    with Live(table_generator(old_flags.values()), auto_refresh=False) as live:
        for i in range(int(timeout / pollrate)):
            if len(flags) == len(finished_flags):
                break

            time.sleep(pollrate)

            flags = [flag for execution_id in executions for flag in
                         request('GET', f'flag/execution/{execution_id}')]

            for new_flag in flags:
                if new_flag['id'] in old_flags:
                    old_flag = old_flags[new_flag['id']]

                    new_flag['status_list'] = old_flag['status_list']
                    if old_flag['status_list'][-1] != new_flag['status']:
                        new_flag['status_list'] += [new_flag['status']]
                else:
                    new_flag['status_list'] = [new_flag['status']]

                if new_flag['status'] in FLAG_STATUS_IS_FINAL:
                    finished_flags[new_flag['id']] = new_flag

            live.update(table_generator(flags), refresh=True)
            old_flags = {flag['id']: flag for flag in flags}

    if show_detail:
        print(generate_summary(flags))


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

    response = request('POST', 'flag/submit', data={
        'flags': data,
    })

    print("Flags submitted. Polling for results, feel free to abort with CTRL-C")

    time.sleep(0.5)
    poll_and_show_flags(response['execution_id'], force_detail=True)


@app.command("ids", help="Print flagids")
def flag_ids(
        service: Optional[str] = typer.Argument(default=None, help='Service ID'),
        target_ips: List[str] = typer.Option(RUNLOCAL_TARGETS, '--target', '-T', help=
        'Which Targets to print flag ids (you can specify this option multiple times).'),
        no_target_ips: List[str] = typer.Option([], '-N', '--no-target', help=
        'Which Targets to exclude (you can specify this option multiple times).'),
        all_targets: bool = typer.Option(False, '--all-targets', help=
        'All targets (overrides --target).'),
        ignore_exclusions: bool = typer.Option(True, help=
        'Ignore static exclusions, i.e. excluding our own vulnbox.'),
):
    targets = get_targets(service=None, all_targets=all_targets, target_ips=target_ips, no_target_ips=no_target_ips,
                          ignore_exclusions=ignore_exclusions)

    services = set([target['service'] for target in targets])
    targets_by_service = {service: [target for target in targets if target['service'] == service] for service in
                          services}

    if service is not None:
        if service not in services:
            print(f'{ERROR_STR}: unknown service "{service}". Available services: {magentify(", ".join(services))}.')
            raise typer.Exit(code=1)

        targets_by_service = {service: targets_by_service[service]}

    for service, targets in targets_by_service.items():
        targets_summary = ', '.join(t['ip'] for t in targets)
        print(f'[*] Flag IDs for service {greenify(service)}')
        for t in targets:
            print(f'  {blueify(t["ip"])} => {t["extra"]}')
