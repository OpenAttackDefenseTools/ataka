from .config import engine, Base, async_session as get_session


async def connect():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def disconnect():
    await engine.dispose()
