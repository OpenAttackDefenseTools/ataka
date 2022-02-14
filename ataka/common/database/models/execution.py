import enum

from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, UnicodeText, Enum
from sqlalchemy.orm import relationship

from ..config import Base, JsonBase


class ExecutionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    FINISHED = "finished"


class Execution(Base, JsonBase):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    target_id = Column(Integer, ForeignKey("targets.id"))
    status = Column(Enum(ExecutionStatus))
    stdout = Column(UnicodeText)
    stderr = Column(UnicodeText)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="executions")
    target = relationship("Target")
    flags = relationship("Flag", back_populates="execution")
