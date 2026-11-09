"""Minimal asyncio event bus for in-process application events."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        if not event_type:
            raise ValueError("Event type cannot be empty.")
        self._handlers[event_type].append(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        for handler in tuple(self._handlers.get(event_type, ())):
            await handler(payload)


class BoundedEventQueue:
    """Bound producer growth; callers receive an explicit back-pressure error."""

    def __init__(self, maxsize: int = 1024):
        if maxsize < 1:
            raise ValueError("Queue maxsize must be positive.")
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)

    def put_nowait(self, event: dict[str, Any]) -> None:
        self._queue.put_nowait(event)

    async def get(self) -> dict[str, Any]:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()
