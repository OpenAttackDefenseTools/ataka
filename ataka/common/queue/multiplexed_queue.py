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
        if self._consumer_tag is None:
            self._consumer_tag = consumer_tag

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

    def __getattr__(self, item):
        return getattr(self._queue, item)

    def __aiter__(self, ):
        return self.iterator()

    def iterator(self, *args, **kwargs):
        return QueueIterator(self, *args, **kwargs)
