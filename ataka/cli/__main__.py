import asyncio
from functools import update_wrapper

import typer
from aio_pika import Message
from pamqp.specification import Basic

from ataka.common import queue, control_message


def coro(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return update_wrapper(wrapper, f)


app = typer.Typer()


@app.command()
@coro
async def submit_flag(flag: str):
    await queue.connect()

    channel = await queue.get_channel()
    result = await channel.default_exchange.publish(Message(body=flag.encode()), routing_key='flags')
    if isinstance(result, Basic.Ack):
        print("Submitting...")
    else:
        print(result)

    await channel.close()


@app.command()
@coro
async def reload():
    await queue.connect()

    channel = await queue.get_channel()
    result = await channel.default_exchange.publish(Message(body=control_message.RELOAD_CONFIG), routing_key='control')
    if isinstance(result, Basic.Ack):
        print("OK")
    else:
        print(result)

    await channel.close()


app()
