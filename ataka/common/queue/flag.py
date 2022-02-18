from dataclasses import dataclass

from .queue import WorkQueue, Message, PubSubQueue


@dataclass
class FlagMessage(Message):
    flag_id: int
    flag: str


@dataclass
class FlagNotifyMessage(Message):
    flag_id: int
    manual_id: int
    execution_id: int


class FlagQueue(WorkQueue):
    queue_name = "flag"
    message_type = FlagMessage


class FlagNotifyQueue(PubSubQueue):
    queue_name = "flag_notify"
    message_type = FlagNotifyMessage
