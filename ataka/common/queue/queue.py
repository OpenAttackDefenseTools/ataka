import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict

import aio_pika

from ataka.common.queue.multiplexed_queue import MultiplexedQueue


@dataclass
class Message:
    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_bytes(cls, body: bytes):
        return cls(**json.loads(body.decode()))


class Queue(ABC):
    queue_name: str
    message_type: type[Message]

    _channel: aio_pika.Channel

    @classmethod
    async def get(cls, channel):
        self = cls()
        self._channel = channel
        return self

    @abstractmethod
    async def _get_exchange(self) -> aio_pika.Exchange:
        pass

    @abstractmethod
    async def _get_queue(self) -> aio_pika.Queue:
        pass

    # send a message message
    async def send_message(self, message):
        exchange = await self._get_exchange()
        return await exchange.publish(aio_pika.Message(body=self.message_type.to_bytes(message)),
                                      routing_key=self.queue_name)

    # a generator to return messages as they are received (endless loop)
    async def wait_for_messages(self, **kwargs):
        async with (await self._get_queue()).iterator(**kwargs) as queue_iter:
            async for message in queue_iter:
                async with message.process(ignore_processed=True):
                    yield self.message_type.from_bytes(message.body)

    async def clear(self):
        queue = await self._get_queue()
        return await queue.purge()


class PubSubQueue(Queue):
    _exchange: aio_pika.Exchange = None
    _queue: aio_pika.Queue = None

    async def _get_exchange(self) -> aio_pika.Exchange:
        if self._exchange is None:
            self._exchange = await self._channel.declare_exchange(self.queue_name, aio_pika.ExchangeType.FANOUT)
        return self._exchange

    async def _get_queue(self) -> aio_pika.Queue:
        if self._queue is None:
            self._queue = MultiplexedQueue(await self._channel.declare_queue(exclusive=True))
            await self._queue.bind(await self._get_exchange())
        return self._queue


class WorkQueue(Queue):
    _queue: aio_pika.Queue = None

    async def _get_exchange(self) -> aio_pika.Exchange:
        return self._channel.default_exchange

    async def _get_queue(self) -> aio_pika.Queue:
        if self._queue is None:
            self._queue = await self._channel.declare_queue(name=self.queue_name, durable=True)
        return self._queue
