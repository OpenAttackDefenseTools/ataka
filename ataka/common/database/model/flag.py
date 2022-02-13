from sqlalchemy import Column, Integer, String, DateTime, func

from ..config import Base, JsonBase


class Flag(Base, JsonBase):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True)
    flag = Column(String, index=True)
    status = Column(String)  # one of flag_status.py
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
