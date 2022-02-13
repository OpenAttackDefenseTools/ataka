from ataka.common.database.model.flag import Flag
from .queue import WorkQueue


class FlagQueue(WorkQueue):
    queue_name = "flag"

    @staticmethod
    def serialize(message: Flag) -> bytes:
        print(f"Serializing {message} to {message.to_json()}")
        return message.to_json().encode()

    @staticmethod
    def parse(body: bytes) -> Flag:
        return Flag.from_json(body.decode())
