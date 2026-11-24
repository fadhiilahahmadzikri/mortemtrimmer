# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Thread-safe in-memory domain event bus."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict

from autosilenttrimmer.domain.contracts.event_bus import EventHandler, IEventBus
from autosilenttrimmer.domain.models.events import DomainEvent

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """Synchronous thread-safe event bus with subclass dispatch."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register handler for target event type."""
        with self._lock:
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        """Publish event to concrete subscribers and DomainEvent wildcard listeners."""
        with self._lock:
            targets = list(self._handlers.get(type(event), []))
            if type(event) is not DomainEvent:
                targets.extend(self._handlers.get(DomainEvent, []))

        for handler in targets:
            try:
                handler(event)
            except Exception as exc:
                logger.warning("Event subscriber failed for %s: %s", type(event).__name__, exc)
