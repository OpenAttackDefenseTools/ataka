from sqlalchemy import Column, Integer, String, DateTime, func, Index

from ..config import Base, JsonBase


class Target(Base, JsonBase):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, index=True)
    ip = Column(String)
    service = Column(String, index=True)
    extra = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index('service_version_index', "service", "version"), )
