import enum


class JobExecutionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    FINISHED = "finished"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
