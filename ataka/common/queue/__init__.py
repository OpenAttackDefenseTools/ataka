import asyncio
import os

import aio_pika
from aio_pika import RobustConnection

from .control import *
from .flag import *
from .job import *

connection: RobustConnection = None


async def connect():
    global connection
    connection = await aio_pika.connect_robust(host="rabbitmq", login=os.environ["RABBITMQ_USER"],
                                               password=os.environ["RABBITMQ_PASSWORD"],
                                               loop=asyncio.get_running_loop())


async def disconnect():
    global connection
    await connection.close()


async def get_channel():
    return await connection.channel()
