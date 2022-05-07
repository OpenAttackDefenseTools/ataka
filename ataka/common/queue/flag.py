from dataclasses import dataclass
from typing import Optional

from .queue import WorkQueue, Message, PubSubQueue


@dataclass
class FlagMessage(Message):
    flag_id: int
    flag: str


@dataclass
class FlagNotifyMessage(Message):
    flag_id: int
    manual_id: int | None
    execution_id: None | int


class FlagQueue(WorkQueue):
    queue_name = "flag"
    message_type = FlagMessage


class FlagNotifyQueue(PubSubQueue):
    queue_name = "flag_notify"
    message_type = FlagNotifyMessage
