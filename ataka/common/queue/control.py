from enum import Enum

from .queue import PubSubQueue


class ControlMessage(Enum):
    RELOAD_CONFIG = b"reload_config"


class ControlQueue(PubSubQueue):
    queue_name = "control"

    @staticmethod
    def serialize(message: ControlMessage) -> bytes:
        return message.value

    @staticmethod
    def parse(body: bytes) -> ControlMessage:
        return ControlMessage(body)
