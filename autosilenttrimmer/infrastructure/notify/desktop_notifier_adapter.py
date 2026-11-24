# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Cross-platform native desktop notifications powered by MIT desktop-notifier."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading

from autosilenttrimmer.core.constants import APP_NAME
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.contracts.notifier import INotifier

logger = logging.getLogger(__name__)


def _open_file_os(path: str) -> None:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return
    if os.name == "nt":
        os.startfile(abs_path)  # type: ignore[attr-defined]
    elif os.uname().sysname == "Darwin":  # type: ignore[attr-defined]
        subprocess.Popen(["open", abs_path])
    else:
        subprocess.Popen(["xdg-open", abs_path])


def _reveal_in_folder_os(path: str) -> None:
    abs_path = os.path.abspath(path)
    if os.name == "nt":
        subprocess.Popen(["explorer", "/select,", abs_path])
    elif os.uname().sysname == "Darwin":  # type: ignore[attr-defined]
        subprocess.Popen(["open", "-R", abs_path])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(abs_path)])


class DesktopNotifierAdapter(INotifier):
    """Sends non-blocking WinRT/Cocoa/DBus toast notifications with action buttons."""

    def __init__(self, localizer: Localizer, enabled: bool = True) -> None:
        self._l10n = localizer
        self._enabled = enabled
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._notifier = self._init_notifier()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @staticmethod
    def _init_notifier() -> object | None:
        try:
            from desktop_notifier import DesktopNotifier

            return DesktopNotifier(app_name=APP_NAME)
        except Exception as exc:
            logger.debug("desktop-notifier unavailable in this session: %s", exc)
            return None

    def notify_completed(
        self,
        output_path: str,
        original_duration: float,
        final_duration: float,
        reduction_percentage: float,
    ) -> None:
        """Emit completion toast with Open File & Show in Folder action buttons."""
        if not self._enabled or self._notifier is None:
            return
        title = self._l10n.text("notify.completed_title")
        filename = os.path.basename(output_path)
        body = self._l10n.text(
            "notify.completed_body", filename=filename, reduction=reduction_percentage
        )

        async def _send() -> None:
            from desktop_notifier import Button

            await self._notifier.send(  # type: ignore[attr-defined]
                title=title,
                message=body,
                buttons=[
                    Button(
                        title=self._l10n.text("notify.action_open"),
                        on_pressed=lambda: _open_file_os(output_path),
                    ),
                    Button(
                        title=self._l10n.text("notify.action_folder"),
                        on_pressed=lambda: _reveal_in_folder_os(output_path),
                    ),
                ],
            )

        self._dispatch(_send())

    def notify_failed(self, source_path: str, error_code: str, message: str) -> None:
        """Emit localized failure toast referencing stable ErrorCode."""
        if not self._enabled:
            return
        if self._notifier is None:
            raise RuntimeError("Native desktop notifier backend is unavailable.")
        title = f"{self._l10n.text('notify.failed_title')} ({error_code})"
        body = f"{os.path.basename(source_path)}: {message}"

        async def _send() -> None:
            await self._notifier.send(title=title, message=body)  # type: ignore[attr-defined]

        self._dispatch(_send())

    def notify_info(self, title: str, message: str) -> None:
        """Emit informational toast (e.g. GPU->CPU Policy G2 fallback)."""
        if not self._enabled or self._notifier is None:
            return

        async def _send() -> None:
            await self._notifier.send(title=title, message=message)  # type: ignore[attr-defined]

        self._dispatch(_send())

    def _dispatch(self, coro: object) -> None:
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type]
            future.result(timeout=3.0)
        except Exception as exc:
            logger.debug("Toast delivery skipped/suppressed: %s", exc)
            raise RuntimeError(str(exc)) from exc
