import asyncio
from typing import Callable, Any

import aiormq
from aio_pika import Queue, IncomingMessage
from aio_pika.queue import ConsumerTag, QueueIterator


class MultiplexedQueue(Queue):
    def __init__(self, queue: Queue):
        self._queue = queue
        self._consuming = False
        self._consumers = 0
        self._callbacks = {}
        self._consumer_tag = None

    async def consume(
            self,
            callback: Callable[[IncomingMessage], Any],
            no_ack: bool = False,
            exclusive: bool = False,
            arguments: dict = None,
            consumer_tag=None,
            timeout=None,
    ) -> ConsumerTag:
        if self._consumer_tag is not None and self._consumer_tag is not consumer_tag:
            raise ValueError("Consumer tags of subsequent calls do not match")

        self._consumers += 1

        if not self._consuming:
            self._consuming = True
            self._consumer_tag = await self._queue.consume(self.call_consumers, no_ack, exclusive, arguments,
                                                           self._consumer_tag, timeout)

        tag = f"{self._consumer_tag}-{str(self._consumers)}"
        self._callbacks[tag] = callback
        return tag

    async def cancel(
            self, consumer_tag: ConsumerTag, timeout=None, nowait: bool = False
    ) -> aiormq.spec.Basic.CancelOk:
        self._consumers -= 0

        del self._callbacks[consumer_tag]
        return aiormq.spec.Basic.CancelOk(consumer_tag)

    async def call_consumers(self, message: IncomingMessage):
        await asyncio.gather(*[callback(message) for callback in self._callbacks.values()])

    @property
    def channel(self) -> aiormq.Channel:
        return self._queue.channel

    @property
    def loop(self):
        return self._queue.loop

    @property
    def name(self):
        return self._queue.name

    @property
    def durable(self):
        return self._queue.durable

    @property
    def exclusive(self):
        return self._queue.exclusive

    @property
    def auto_delete(self):
        return self._queue.auto_delete

    @property
    def arguments(self):
        return self._queue.arguments

    @property
    def passive(self):
        return self._queue.passive

    @property
    def declaration_result(self):
        return self._queue.declaration_result

    async def declare(self, *args, **kwargs):
        return await self._queue.declare(*args, **kwargs)

    async def bind(self, *args, **kwargs):
        return await self._queue.bind(*args, **kwargs)

    async def unbind(self, *args, **kwargs):
        return await self._queue.unbind(*args, **kwargs)

    async def get(self, *args, **kwargs):
        return await self._queue.get(*args, **kwargs)

    async def purge(self, *args, **kwargs):
        return await self._queue.purge(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._queue.delete(*args, **kwargs)

    def __aiter__(self, ):
        return self.iterator()

    def iterator(self, *args, **kwargs):
        return QueueIterator(self, **kwargs)
