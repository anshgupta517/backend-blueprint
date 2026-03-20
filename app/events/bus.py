# app/events/bus.py
import asyncio
from typing import Callable, Type
from collections import defaultdict
from app.events.definitions import BaseEvent
from app.core.logging import logger


class EventBus:
    """
    Lightweight async publish/subscribe event bus.

    Publishers call bus.publish(event) — they don't know who's listening.
    Handlers register for specific event types — they don't know who publishes.
    This is the entire contract. Neither side depends on the other.

    All handlers for an event run concurrently via asyncio.gather.
    One handler failing doesn't affect others.
    """

    def __init__(self):
        # Maps event type → list of handler functions
        self._handlers: dict[Type[BaseEvent], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[BaseEvent], handler: Callable) -> None:
        """
        Register a handler for an event type.
        Called at startup — not per request.
        """
        self._handlers[event_type].append(handler)
        logger.info(
            f"Handler registered: {handler.__name__} → {event_type.__name__}"
        )

    async def publish(self, event: BaseEvent) -> None:
        """
        Publish an event — all registered handlers run concurrently.
        If a handler raises an exception it's logged but doesn't
        propagate back to the publisher or affect other handlers.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.info(f"Event published with no handlers: {event_type.__name__}")
            return

        logger.info(
            f"Publishing {event_type.__name__} to {len(handlers)} handler(s)"
        )

        # Run all handlers concurrently
        # Each handler gets its own try/except — one failure is isolated
        async def run_handler(handler):
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} failed for "
                    f"{event_type.__name__}: {e}",
                    exc_info=True,
                )

        await asyncio.gather(*[run_handler(h) for h in handlers])


# Module-level singleton — import this everywhere
event_bus = EventBus()