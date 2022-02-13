import asyncio
from functools import update_wrapper
from typing import List

import typer
from pamqp.specification import Basic

from ataka.common import queue, database
from ataka.common.database.models import Flag, FlagStatus
from ataka.common.queue import get_channel, ControlQueue, ControlMessage, FlagQueue


def coro(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return update_wrapper(wrapper, f)


app = typer.Typer()


@app.command()
@coro
async def submit_flag(flag: List[str]):
    await queue.connect()
    await database.connect()

    async with database.get_session() as session:
        flag_objects = [Flag(flag=f, status=FlagStatus.QUEUED) for f in flag]
        session.add_all(flag_objects)
        await session.commit()

        async with await queue.get_channel() as channel:
            flag_queue = await FlagQueue.get(channel)
            for flag_object in flag_objects:
                result = await flag_queue.send_message(flag_object)
                if isinstance(result, Basic.Ack):
                    print(f"Submitted {flag_object.flag}")
                else:
                    print(result)

    await queue.disconnect()
    await database.disconnect()


@app.command()
@coro
async def reload():
    await queue.connect()

    channel = await get_channel()
    controlQueue = await ControlQueue.get(channel)
    result = await controlQueue.send_message(ControlMessage.RELOAD_CONFIG)
    if isinstance(result, Basic.Ack):
        print("OK")
    else:
        print(result)

    await queue.disconnect()


app()
