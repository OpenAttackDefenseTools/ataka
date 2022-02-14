from dataclasses import dataclass
from enum import Enum

from .queue import WorkQueue, Message


class JobAction(str, Enum):
    QUEUE = "queue"
    CANCEL = "cancel"


@dataclass
class JobMessage(Message):
    action: JobAction
    job_id: int


class JobQueue(WorkQueue):
    queue_name = "job"
    message_type = JobMessage
