from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from app.runtime.events import Event, EventType


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Central asynchronous event bus for AEGIS.

    Supports:
    - event-specific subscribers
    - global subscribers
    - concurrent handler execution
    - safe unsubscribe
    - handler failure isolation
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

        self._lock = asyncio.Lock()

        self._logger = logging.getLogger(
            "aegis.event_bus"
        )

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        handlers = self._handlers.get(event_type)

        if not handlers:
            return

        try:
            handlers.remove(handler)
        except ValueError:
            return

        if not handlers:
            self._handlers.pop(event_type, None)

    def subscribe_all(
        self,
        handler: EventHandler,
    ) -> None:
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)

    def unsubscribe_all(
        self,
        handler: EventHandler,
    ) -> None:
        try:
            self._global_handlers.remove(handler)
        except ValueError:
            pass

    async def publish(
        self,
        event: Event,
    ) -> None:
        specific_handlers = tuple(
            self._handlers.get(event.type, ())
        )

        global_handlers = tuple(
            self._global_handlers
        )

        handlers = []

        for handler in (
            *specific_handlers,
            *global_handlers,
        ):
            if handler not in handlers:
                handlers.append(handler)

        if not handlers:
            return

        results = await asyncio.gather(
            *(
                handler(event)
                for handler in handlers
            ),
            return_exceptions=True,
        )

        for handler, result in zip(
            handlers,
            results,
        ):
            if isinstance(result, Exception):
                self._logger.error(
                    "Event handler failed",
                    extra={
                        "event_type": event.type.value,
                        "event_id": str(event.event_id),
                        "handler": getattr(
                            handler,
                            "__qualname__",
                            repr(handler),
                        ),
                    },
                    exc_info=(
                        type(result),
                        result,
                        result.__traceback__,
                    ),
                )

    async def publish_many(
        self,
        events: list[Event],
    ) -> None:
        for event in events:
            await self.publish(event)

    def clear(self) -> None:
        self._handlers.clear()
        self._global_handlers.clear()