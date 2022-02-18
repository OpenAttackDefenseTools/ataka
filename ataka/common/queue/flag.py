from dataclasses import dataclass

from .queue import WorkQueue, Message, PubSubQueue
from ..database.models import FlagStatus


@dataclass
class FlagMessage(Message):
    flag_id: int
    flag: str


@dataclass
class FlagNotifyMessage(FlagMessage):
    status: FlagStatus


class FlagQueue(WorkQueue):
    queue_name = "flag"
    message_type = FlagMessage


class FlagNotifyQueue(PubSubQueue):
    queue_name = "flag_notify"
    message_type = FlagNotifyMessage
