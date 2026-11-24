# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Event bus contract decoupling job execution from UI and notifications."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from autosilenttrimmer.domain.models.events import DomainEvent

EventHandler = Callable[[DomainEvent], None]


class IEventBus(ABC):
    """Pub/sub domain event dispatcher."""

    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register handler for a specific DomainEvent type (or DomainEvent base)."""
        pass

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Dispatch event synchronously or cleanly to registered subscribers."""
        pass
