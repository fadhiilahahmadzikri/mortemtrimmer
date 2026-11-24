# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Single-instance IPC gateway contract (Doc 01 §5, §9 Multi-Select)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class IIPCGateway(ABC):
    """Background IPC server receiving multi-select file batches and control signals."""

    @abstractmethod
    def start(
        self,
        on_batch_received: Callable[[list[str]], None],
        on_reload_settings: Callable[[], None] | None = None,
    ) -> None:
        """Start listening on OS-native pipe/socket and coalesce bursts."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Gracefully shut down IPC server and release endpoint."""
        pass


class IJobGatewayClient(ABC):
    """Thin client invoked by Explorer shell shim or Tune UI to talk to running daemon."""

    @abstractmethod
    def is_daemon_running(self) -> bool:
        """Check whether background job gateway daemon is accepting requests."""
        pass

    @abstractmethod
    def enqueue_paths(self, paths: list[str]) -> bool:
        """Send file paths over IPC to running daemon; return True if acknowledged."""
        pass

    @abstractmethod
    def notify_settings_updated(self) -> bool:
        """Signal running daemon to hot-reload persisted UserSettings."""
        pass
