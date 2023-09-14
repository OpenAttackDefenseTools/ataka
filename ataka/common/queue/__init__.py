import asyncio
import os
from contextlib import asynccontextmanager

import aio_pika
from aio_pika import RobustConnection

from .flag import *
from .job import *
from .output import *

connection: RobustConnection = None


async def connect():
    global connection
    connection = await aio_pika.connect_robust(host="rabbitmq", login=os.environ["RABBITMQ_USER"],
                                               password=os.environ["RABBITMQ_PASSWORD"],
                                               loop=asyncio.get_running_loop())


async def disconnect():
    global connection
    await connection.close()


@asynccontextmanager
async def get_channel():
    async with await connection.channel() as channel:
        yield channel
