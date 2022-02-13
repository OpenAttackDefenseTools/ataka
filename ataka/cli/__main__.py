import asyncio
from functools import update_wrapper
from typing import List

import typer
from pamqp.specification import Basic

from ataka.common import queue
from ataka.common.database.model.flag import Flag
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

    channel = await queue.get_channel()

    flag_queue = await FlagQueue.get(channel)
    for f in flag:
        result = await flag_queue.send_message(Flag(flag=f))
        if isinstance(result, Basic.Ack):
            print(f"Submitted {f}")
        else:
            print(result)

    await queue.disconnect()


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
