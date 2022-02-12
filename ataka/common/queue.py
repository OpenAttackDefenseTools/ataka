import asyncio
import os

import aio_pika

connection = None


async def connect():
    global connection
    connection = await aio_pika.connect_robust(host="rabbitmq", login=os.environ["RABBITMQ_USER"],
                                               password=os.environ["RABBITMQ_PASSWORD"],
                                               loop=asyncio.get_running_loop())


async def get_channel():
    global connection
    return await connection.channel()
