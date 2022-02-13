import json
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

user = os.environ['POSTGRES_USER']
password = os.environ['POSTGRES_PASSWORD']

engine = create_async_engine(f"postgresql+asyncpg://{user}:{password}@postgres/{user}", future=True, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


class JsonBase:
    def to_json(self):
        return json.dumps({c.name: getattr(self, c.name) for c in self.__table__.columns})

    @classmethod
    def from_json(cls, string):
        return cls(**json.loads(string))
