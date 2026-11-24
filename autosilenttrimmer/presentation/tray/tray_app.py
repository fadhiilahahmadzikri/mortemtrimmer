"""Lightweight cross-platform 'Hex Flow' system tray UI powered by pystray."""

from __future__ import annotations

import contextlib
import logging
import os
import threading
from collections.abc import Callable

from autosilenttrimmer.core.constants import APP_NAME
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.contracts.event_bus import IEventBus
from autosilenttrimmer.domain.contracts.ui import ITrayUI
from autosilenttrimmer.domain.models.events import (
    DomainEvent,
    JobCancelled,
    JobCompleted,
    JobFailed,
    JobQueued,
    JobStarted,
    ProgressUpdated,
)
from autosilenttrimmer.presentation.theme import format_error_code_label, resolve_asset_path
from autosilenttrimmer.presentation.tray.progress_popup import MinimalProgressPopup
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def _create_tray_icon_image() -> Image.Image:
    """Load the Mortem Primer blade emblem bitmap or draw a gold-and-brown fallback."""
    tray_asset = resolve_asset_path("mortem_tray.png")
    if tray_asset is not None:
        return Image.open(tray_asset).convert("RGBA")

    img = Image.new("RGBA", (64, 64), (22, 18, 15, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([4, 4, 60, 60], radius=12, outline=(217, 154, 43, 255), width=3)
    draw.rectangle([16, 26, 24, 38], fill=(217, 154, 43, 255))
    draw.rectangle([28, 16, 36, 48], fill=(243, 192, 91, 255))
    draw.rectangle([40, 22, 48, 42], fill=(217, 154, 43, 255))
    return img


class PystrayTrayUI(ITrayUI):
    """System tray controller + minimal progress overlay subscribing to IEventBus."""

    def __init__(self, event_bus: IEventBus, localizer: Localizer) -> None:
        self._bus = event_bus
        self._l10n = localizer
        self._icon = None
        self._popup: MinimalProgressPopup | None = None
        self._status_text = self._l10n.text("tray.status_idle")
        self._thread: threading.Thread | None = None

    def start(
        self,
        *,
        on_open_tune: Callable[[], None],
        on_open_logs: Callable[[], None],
        on_pause_toggle: Callable[[], None],
        on_cancel_current: Callable[[], None],
        on_export_diagnostics: Callable[[], str],
        on_toggle_language: Callable[[], str],
        on_quit: Callable[[], None],
    ) -> None:
        """Start pystray icon and minimal progress popup subscribing cleanly to DomainEvents."""
        import pystray

        self._popup = MinimalProgressPopup(
            self._l10n,
            on_pause_toggle=on_pause_toggle,
            on_cancel=on_cancel_current,
            on_open_logs=on_open_logs,
        )
        self._popup.start()

        def _on_event(event: DomainEvent) -> None:
            if isinstance(event, JobQueued):
                self._status_text = self._l10n.text(
                    "tray.status_queued",
                    filename=os.path.basename(event.source_path),
                )
            elif isinstance(event, JobStarted):
                self._status_text = self._l10n.text(
                    "tray.status_running",
                    percent=1.0,
                    filename=os.path.basename(event.source_path),
                )
            elif isinstance(event, ProgressUpdated):
                self._status_text = self._l10n.text(
                    "tray.status_running",
                    percent=event.percent,
                    filename=event.filename,
                )
            elif isinstance(event, JobCompleted):
                self._status_text = self._l10n.text(
                    "tray.status_completed",
                    filename=os.path.basename(event.output_path or event.source_path),
                    reduction=event.reduction_percentage,
                )
            elif isinstance(event, JobFailed):
                self._status_text = self._l10n.text(
                    "tray.status_failed",
                    filename=os.path.basename(event.source_path),
                    error_code=format_error_code_label(event.error_code or ""),
                )
            elif isinstance(event, JobCancelled):
                self._status_text = self._l10n.text("tray.status_idle")

            if self._popup is not None:
                self._popup.push_event(event)
            if self._icon is not None:
                self._icon.title = self._status_text[:127]
                with contextlib.suppress(Exception):
                    self._icon.update_menu()

        self._bus.subscribe(DomainEvent, _on_event)

        def _export_diag(_icon: object, _item: object) -> None:
            zip_path = on_export_diagnostics()
            self.show_balloon(APP_NAME, f"Diagnostics saved: {zip_path}")

        def _toggle_lang(_icon: object, _item: object) -> None:
            new_lang = on_toggle_language()
            self.show_balloon(APP_NAME, f"Language switched to {new_lang.upper()}")

        def _quit_app(icon: pystray.Icon, _item: object) -> None:
            on_quit()
            self.stop()
            icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem(lambda _item: self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _item: self._l10n.text("tray.action_tune"),
                lambda _icon, _item: on_open_tune(),
                default=True,
            ),
            pystray.MenuItem(
                lambda _item: self._l10n.text("tray.action_logs"),
                lambda _icon, _item: on_open_logs(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _item: self._l10n.text("tray.action_pause"),
                lambda _icon, _item: on_pause_toggle(),
            ),
            pystray.MenuItem(
                lambda _item: self._l10n.text("tray.action_cancel"),
                lambda _icon, _item: on_cancel_current(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _item: self._l10n.text("tray.action_export_diag"), _export_diag
            ),
            pystray.MenuItem(lambda _item: self._l10n.text("tray.action_language"), _toggle_lang),
            pystray.MenuItem(lambda _item: self._l10n.text("tray.action_quit"), _quit_app),
        )

        self._icon = pystray.Icon(
            "MortemPrimer",
            _create_tray_icon_image(),
            title=self._status_text,
            menu=menu,
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def show_balloon(self, title: str, message: str) -> None:
        """Fallback tray notification if WinRT/OS native toast is suppressed."""
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception as exc:
                logger.debug("Tray balloon failed: %s", exc)

    def stop(self) -> None:
        """Terminate progress popup and tray icon."""
        if self._popup is not None:
            self._popup.stop()
        if self._icon is not None:
            with contextlib.suppress(Exception):
                self._icon.stop()
