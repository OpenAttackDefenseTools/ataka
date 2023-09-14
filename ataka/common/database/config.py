import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

user = os.environ['POSTGRES_USER']
password = os.environ['POSTGRES_PASSWORD']

engine = create_async_engine(f"postgresql+asyncpg://{user}:{password}@postgres/{user}") #, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


class JsonBase:
    def to_dict(self):
        return {c.name: self.__dict__[c.name] if c.name in self.__dict__ else None for c in self.__table__.columns}

    @classmethod
    def from_dict(cls, dict):
        return cls(**dict)
