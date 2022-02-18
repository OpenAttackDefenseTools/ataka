import enum

from sqlalchemy import Column, Integer, String, DateTime, func, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from ..config import Base, JsonBase


class FlagStatus(str, enum.Enum):
    UNKNOWN = 'unknown'

    # everything is fine
    OK = 'ok'

    # Flag is currently being submitted
    QUEUED = 'queued'

    # Flag is currently being submitted
    PENDING = 'pending'

    # We already submitted this flag and the submission system tells us thats
    DUPLICATE = 'duplicate'

    # something is wrong with our submitter
    ERROR = 'error'

    # the service did not check the flag, but told us to fuck off
    RATELIMIT = 'ratelimit'

    # something is wrong with the submission system
    EXCEPTION = 'exception'

    # we tried to submit our own flag and the submission system lets us know
    OWNFLAG = 'ownflag'

    # the flag is not longer active. This is used if a flags are restricted to a
    # specific time frame
    INACTIVE = 'inactive'

    # flag fits the format and could be sent to the submission system, but the
    # submission system told us it is invalid
    INVALID = 'invalid'

    # This status code is used in case the scoring system requires the services to
    # be working. Flags that are rejected might be sent again!
    SERVICEBROKEN = 'servicebroken'


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
