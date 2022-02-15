from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, Enum, String
from sqlalchemy.orm import relationship

from .jobexecutionstatus import JobExecutionStatus
from ..config import Base, JsonBase


class Job(Base, JsonBase):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    exploit_id = Column(String, ForeignKey("exploits.id"), index=True)
    status = Column(Enum(JobExecutionStatus), index=True)
    timeout = Column(DateTime(timezone=True))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    exploit = relationship("Exploit")
    executions = relationship("Execution", back_populates="job")
