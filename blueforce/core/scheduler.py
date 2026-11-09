"""Small task scheduler with bounded lifecycle and cancellation support."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class Scheduler:
    def __init__(self):
        self._tasks: set[asyncio.Task] = set()

    def start(self, coroutine: Awaitable) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def close(self) -> None:
        for task in tuple(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def run_periodic(self, callback: Callable[[], Awaitable[None]],
                           interval: float) -> None:
        if interval <= 0:
            raise ValueError("Periodic interval must be positive.")
        while True:
            await callback()
            await asyncio.sleep(interval)
