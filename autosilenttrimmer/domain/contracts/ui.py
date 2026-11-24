"""Minimal 'Hex Flow' Tray UI and compact progress overlay contract (Doc 01 A2)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class ITrayUI(ABC):
    """Minimal tray icon & unobtrusive progress overlay abstraction."""

    @abstractmethod
    def start(
        self,
        *,
        on_open_tune: Callable[[], None],
        on_pause_toggle: Callable[[], None],
        on_cancel_current: Callable[[], None],
        on_export_diagnostics: Callable[[], str],
        on_toggle_language: Callable[[], str],
        on_quit: Callable[[], None],
    ) -> None:
        """Start tray event loop wiring UI actions cleanly to application handlers."""
        pass

    @abstractmethod
    def show_balloon(self, title: str, message: str) -> None:
        """Tray notification fallback when OS native toasts are suppressed (DND/Focus Assist)."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Shut down tray UI and overlay widgets cleanly."""
        pass
