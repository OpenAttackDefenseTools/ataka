from sqlalchemy import Column, Integer, ForeignKey, UnicodeText, Enum, DateTime, func
from sqlalchemy.orm import relationship

from ataka.common.job_execution_status import JobExecutionStatus
from ..config import Base, JsonBase


class Execution(Base, JsonBase):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    target_id = Column(Integer, ForeignKey("targets.id"))
    status = Column(Enum(JobExecutionStatus))
    stdout = Column(UnicodeText)
    stderr = Column(UnicodeText)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="executions")
    target = relationship("Target")
    flags = relationship("Flag", back_populates="execution")
