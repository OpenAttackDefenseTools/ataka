from abc import ABC, abstractmethod

import aio_pika
from aio_pika import Message, ExchangeType


class Queue(ABC):
    queue_name: str

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
        return await exchange.publish(Message(body=self.serialize(message)),
                                      routing_key=self.queue_name)

    # a generator to return messages as they are received (endless loop)
    async def wait_for_messages(self, **kwargs):
        async with (await self._get_queue()).iterator(**kwargs) as queue_iter:
            async for message in queue_iter:
                await message.ack()
                yield self.parse(message.body)

    @staticmethod
    @abstractmethod
    def serialize(message) -> bytes:
        pass

    @staticmethod
    @abstractmethod
    def parse(body: bytes):
        pass


class PubSubQueue(Queue, ABC):
    _exchange: aio_pika.Exchange = None
    _queue: aio_pika.Queue = None

    async def _get_exchange(self) -> aio_pika.Exchange:
        if self._exchange is None:
            self._exchange = await self._channel.declare_exchange(self.queue_name, ExchangeType.FANOUT)
        return self._exchange

    async def _get_queue(self) -> aio_pika.Queue:
        if self._queue is None:
            self._queue = await self._channel.declare_queue(exclusive=True)
            await self._queue.bind(await self._get_exchange())
        return self._queue


class WorkQueue(Queue, ABC):
    _queue: aio_pika.Queue = None

    async def _get_exchange(self) -> aio_pika.Exchange:
        return self._channel.default_exchange

    async def _get_queue(self) -> aio_pika.Queue:
        if self._queue is None:
            self._queue = await self._channel.declare_queue(name=self.queue_name, durable=True)
        return self._queue
