"""Native desktop notification contract with action callbacks and DND fallback."""

from __future__ import annotations

from abc import ABC, abstractmethod


class INotifier(ABC):
    """Cross-platform OS notification port with Open File / Show in Folder actions."""

    @abstractmethod
    def notify_completed(
        self,
        output_path: str,
        original_duration: float,
        final_duration: float,
        reduction_percentage: float,
    ) -> None:
        """Show completion notification with open/reveal actions or tray fallback."""
        pass

    @abstractmethod
    def notify_failed(self, source_path: str, error_code: str, message: str) -> None:
        """Show localized failure notification with stable error reference."""
        pass

    @abstractmethod
    def notify_info(self, title: str, message: str) -> None:
        """Show informational notice (e.g. GPU fallback to CPU)."""
        pass
