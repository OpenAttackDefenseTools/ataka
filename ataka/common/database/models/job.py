from sqlalchemy import Column, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship

from ..config import Base, JsonBase


class Job(Base, JsonBase):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    exploit_id = Column(Integer, ForeignKey("exploits.id"), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    exploit = relationship("Exploit")
    executions = relationship("Execution", back_populates="job")
