from dataclasses import dataclass

from .queue import WorkQueue, Message


@dataclass
class FlagMessage(Message):
    flag_id: int
    flag: str


class FlagQueue(WorkQueue):
    queue_name = "flag"
    message_type = FlagMessage
