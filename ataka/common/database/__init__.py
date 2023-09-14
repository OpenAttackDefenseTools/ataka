from contextlib import asynccontextmanager
import traceback

from .config import engine, Base, async_session


async def connect():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def disconnect():
    await engine.dispose()


@asynccontextmanager
async def get_session():
    try:
        async with async_session() as session:
            yield session
    except Exception as e:
        traceback.print_exception(e)
        raise e
