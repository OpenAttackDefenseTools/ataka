from enum import Enum

from .queue import PubSubQueue, Message


class ControlMessage(bytes, Enum):
    RELOAD_CONFIG = b"reload_config"

    def to_bytes(self) -> bytes:
        return self.value

    @classmethod
    def from_bytes(cls, body: bytes):
        return cls(body)


class ControlQueue(PubSubQueue):
    queue_name = "control"
    message_type = ControlMessage
