import asyncio
from functools import update_wrapper
from typing import List

import typer
from pamqp.specification import Basic

from ataka.common import queue, database
from ataka.common.database.models import Flag, FlagStatus
from ataka.common.queue import get_channel, ControlQueue, ControlMessage, FlagQueue, FlagMessage, ControlAction


def coro(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return update_wrapper(wrapper, f)


app = typer.Typer()


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
    async with await queue.get_channel() as channel:
        flag_queue = await FlagQueue.get(channel)
        for message in messages:
            result = await flag_queue.send_message(message)
            if isinstance(result, Basic.Ack):
                print(f"Submitted {message.flag}")
            else:
                print(result)
    await queue.disconnect()


@app.command()
@coro
async def reload():
    await queue.connect()

    channel = await get_channel()
    control_queue = await ControlQueue.get(channel)
    result = await control_queue.send_message(ControlMessage(action=ControlAction.RELOAD_CONFIG))
    if isinstance(result, Basic.Ack):
        print("OK")
    else:
        print(result)

    await queue.disconnect()


app()
