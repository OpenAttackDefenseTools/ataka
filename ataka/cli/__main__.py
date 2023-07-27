import asyncio
from functools import update_wrapper
from typing import List

import typer
from rich import print, box
from rich.table import Table
from rich.live import Live
from pamqp.commands import Basic
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ataka.common import queue, database
from ataka.common.database.models import Flag, FlagStatus, Execution, Job
from ataka.common.queue import FlagQueue, FlagMessage, OutputQueue


def coro(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return update_wrapper(wrapper, f)


app = typer.Typer()


@app.command()
@coro
async def log():
    await queue.connect()
    async with database.get_session() as session:
        async with queue.get_channel() as channel:
            output_queue: OutputQueue = await OutputQueue.get(channel)
            async for message in output_queue.wait_for_messages():
                load_execution = select(Execution) \
                       .where(Execution.id == message.execution_id) \
                       .options(joinedload(Execution.job).joinedload(Job.exploit), joinedload(Execution.target))

                execution = (await session.execute(load_execution)).unique().scalar_one()
                timestamp = execution.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                table = Table(box=box.ROUNDED)
                table.add_column("Timestamp")
                table.add_column("Service")
                table.add_column("Target")
                table.add_column("Exploit ID")
                table.add_column("")
                table.add_column("Log")

                is_manual = execution.job is None or execution.target is None
                error_tag = "[bold red]ERR[/bold red]" if not message.stdout else "   "

                for line in message.output.strip().split("\n"):
                    if is_manual:
                        table.add_row(timestamp, 'MANUAL', '', '', '', line)
                    else:
                        if execution.job.exploit_id is None:
                            table.add_row(timestamp, execution.target.service, execution.target.ip, f'LOCAL {execution.job.manual_id}', error_tag, line)
                        else:
                            table.add_row(timestamp, execution.target.service, execution.target.ip, f'{execution.job.exploit.id} ({execution.job.exploit.author})', error_tag, line)
                print(table)

    await queue.disconnect()


@app.command()
@coro
async def submit_flag(flag: List[str]):
    await database.connect()
    async with database.get_session() as session:
        flag_objects = [Flag(flag=f, status=FlagStatus.QUEUED) for f in flag]
        session.add_all(flag_objects)
        await session.commit()

        messages = [FlagMessage(flag_id=f.id, flag=f.flag) for f in flag_objects]
    await database.disconnect()

    await queue.connect()
    async with queue.get_channel() as channel:
        flag_queue: FlagQueue = await FlagQueue.get(channel)
        for message in messages:
            result = await flag_queue.send_message(message)
            if isinstance(result, Basic.Ack):
                print(f"Submitted {message.flag}")
            else:
                print(result)
    await queue.disconnect()


app()
