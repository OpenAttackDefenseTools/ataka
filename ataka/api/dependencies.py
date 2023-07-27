from ataka.common import queue, database


async def get_session():
    async with database.get_session() as session:
        yield session


async def get_channel():
    async with queue.get_channel() as channel:
        yield channel
