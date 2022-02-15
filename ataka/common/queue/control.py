from dataclasses import dataclass
from enum import Enum

from .queue import PubSubQueue, Message


class ControlAction(str, Enum):
    RELOAD_CONFIG = "reload_config"
    GET_CTF_CONFIG = "get_ctf_config"
    CTF_CONFIG_UPDATE = "ctf_config_update"


@dataclass
class ControlMessage(Message):
    action: ControlAction
    extra: dict = None


class ControlQueue(PubSubQueue):
    queue_name = "control"
    message_type = ControlMessage
