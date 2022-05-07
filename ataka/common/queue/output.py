from dataclasses import dataclass
from typing import Optional

from .queue import Message, PubSubQueue


@dataclass
class OutputMessage(Message):
    manual_id: int | None
    execution_id: None | int
    stdout: bool
    output: str


class OutputQueue(PubSubQueue):
    queue_name = "output"
    message_type = OutputMessage
