from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from threading import RLock
from typing import Any, TypeVar

EventT = TypeVar("EventT")
Handler = Callable[[Any], Awaitable[None] | None]

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type, list[Handler]] = defaultdict(list)
        self._lock = RLock()

    async def subscribe(self, event_type: type[EventT], handler: Handler) -> None:
        self.subscribe_sync(event_type, handler)

    def subscribe_sync(self, event_type: type[EventT], handler: Handler) -> None:
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    async def unsubscribe(self, event_type: type[EventT], handler: Handler) -> None:
        self.unsubscribe_sync(event_type, handler)

    def unsubscribe_sync(self, event_type: type[EventT], handler: Handler) -> None:
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    async def publish(self, event: object) -> None:
        for handler in self._handlers_for(event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Event handler failed for %s", type(event).__name__)

    def publish_sync(self, event: object) -> None:
        for handler in self._handlers_for(event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    asyncio.run(result)
            except Exception:
                logger.exception("Event handler failed for %s", type(event).__name__)

    def publish_nowait(self, event: object) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.publish_sync(event)
            return
        loop.create_task(self.publish(event))

    async def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()

    def _handlers_for(self, event: object) -> list[Handler]:
        with self._lock:
            return list(self._subscribers.get(type(event), []))
