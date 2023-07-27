from dataclasses import dataclass
from typing import Optional

from .queue import Message, PubSubQueue


@dataclass
class OutputMessage(Message):
    execution_id: int
    stdout: bool
    output: str


class OutputQueue(PubSubQueue):
    queue_name = "output"
    message_type = OutputMessage
