"""Composite notifier falling back from OS toast to tray balloon if DND blocks."""

from __future__ import annotations

import logging
import os

from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.contracts.notifier import INotifier
from autosilenttrimmer.domain.contracts.ui import ITrayUI

logger = logging.getLogger(__name__)


class CompositeNotifier(INotifier):
    """Delivers OS toast notifications and falls back to Tray balloon alerts on error/DND."""

    def __init__(
        self,
        primary: INotifier,
        localizer: Localizer,
        tray_ui: ITrayUI | None = None,
    ) -> None:
        self._primary = primary
        self._l10n = localizer
        self._tray = tray_ui

    def bind_tray(self, tray_ui: ITrayUI) -> None:
        """Attach Tray UI instance once initialized for Focus Assist / DND fallback."""
        self._tray = tray_ui

    def notify_completed(
        self,
        output_path: str,
        original_duration: float,
        final_duration: float,
        reduction_percentage: float,
    ) -> None:
        try:
            self._primary.notify_completed(
                output_path, original_duration, final_duration, reduction_percentage
            )
        except Exception:
            if self._tray is not None:
                title = self._l10n.text("notify.completed_title")
                body = self._l10n.text(
                    "notify.completed_body",
                    filename=os.path.basename(output_path),
                    reduction=reduction_percentage,
                )
                self._tray.show_balloon(title, body)

    def notify_failed(self, source_path: str, error_code: str, message: str) -> None:
        try:
            self._primary.notify_failed(source_path, error_code, message)
        except Exception:
            if self._tray is not None:
                title = f"{self._l10n.text('notify.failed_title')} ({error_code})"
                self._tray.show_balloon(title, f"{os.path.basename(source_path)}: {message}")

    def notify_info(self, title: str, message: str) -> None:
        try:
            self._primary.notify_info(title, message)
        except Exception:
            if self._tray is not None:
                self._tray.show_balloon(title, message)
