from sqlalchemy import Column, Integer, String, DateTime, func

from ..config import Base, JsonBase


class Target(Base, JsonBase):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True)
    ip = Column(String)
    service = Column(String, unique=True)
    extra = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
