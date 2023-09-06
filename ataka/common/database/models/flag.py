from sqlalchemy import Column, Integer, String, DateTime, func, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from ..config import Base, JsonBase

from ataka.common.flag_status import FlagStatus

class Flag(Base, JsonBase):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True)
    flag = Column(String, index=True)
    status = Column(Enum(FlagStatus))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    execution_id = Column(Integer, ForeignKey("executions.id"), index=True)
    manual_id = Column(Integer)
    stdout = Column(Boolean)
    start = Column(Integer)
    end = Column(Integer)

    execution = relationship("Execution", back_populates="flags")
