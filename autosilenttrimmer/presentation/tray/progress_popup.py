"""Lightweight 'Hex Flow' Tkinter progress overlay popup (Doc 01 A2)."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

from autosilenttrimmer.core.constants import TRAY_POLL_INTERVAL_SEC
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.models.events import (
    DomainEvent,
    JobCancelled,
    JobCompleted,
    JobFailed,
    ProgressUpdated,
)

logger = logging.getLogger(__name__)


def _format_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    total = round(seconds)
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


class MinimalProgressPopup:
    """Thread-safe unobtrusive bottom-right progress widget without a heavy main window."""

    def __init__(
        self,
        localizer: Localizer,
        *,
        on_pause_toggle: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        self._l10n = localizer
        self._on_pause_toggle = on_pause_toggle
        self._on_cancel = on_cancel
        self._queue: queue.Queue[DomainEvent] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._paused = False

    def push_event(self, event: DomainEvent) -> None:
        """Queue domain progress/terminal events safely from any worker thread."""
        self._queue.put(event)

    def start(self) -> None:
        """Start UI widget thread safely; turns into clean no-op if display is unavailable."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_tk_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Terminate progress popup UI loop."""
        self._stop.set()

    def _run_tk_loop(self) -> None:
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception as exc:
            logger.debug("Tkinter unavailable; skipping progress overlay: %s", exc)
            return

        try:
            root = tk.Tk()
        except Exception as exc:
            logger.debug("Headless session detected; overlay skipped: %s", exc)
            return

        root.title(self._l10n.text("popup.title"))
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#1a1c23")

        width, height = 340, 126
        scr_w = root.winfo_screenwidth()
        scr_h = root.winfo_screenheight()
        root.geometry(f"{width}x{height}+{scr_w - width - 20}+{scr_h - height - 60}")
        root.withdraw()

        frame = tk.Frame(
            root,
            bg="#1a1c23",
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground="#333845",
        )
        frame.pack(fill=tk.BOTH, expand=True)

        title_lbl = tk.Label(
            frame,
            text=self._l10n.text("popup.title"),
            fg="#ffffff",
            bg="#1a1c23",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        title_lbl.pack(fill=tk.X)

        meta_lbl = tk.Label(
            frame, text="", fg="#a0a8b8", bg="#1a1c23", font=("Segoe UI", 8), anchor="w"
        )
        meta_lbl.pack(fill=tk.X, pady=(2, 6))

        bar = ttk.Progressbar(frame, mode="determinate", maximum=100.0)
        bar.pack(fill=tk.X, pady=(0, 8))

        btn_row = tk.Frame(frame, bg="#1a1c23")
        btn_row.pack(fill=tk.X)

        status_lbl = tk.Label(
            btn_row, text="0%", fg="#00e676", bg="#1a1c23", font=("Segoe UI", 9, "bold")
        )
        status_lbl.pack(side=tk.LEFT)

        cancel_btn = tk.Button(
            btn_row,
            text=self._l10n.text("popup.cancel"),
            command=self._on_cancel,
            bg="#3b2328",
            fg="#ff8a80",
            relief=tk.FLAT,
            padx=8,
            font=("Segoe UI", 8),
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        pause_btn = tk.Button(
            btn_row,
            text=self._l10n.text("popup.pause"),
            bg="#262b36",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            font=("Segoe UI", 8),
        )

        def _toggle_pause() -> None:
            self._paused = not self._paused
            key = "popup.resume" if self._paused else "popup.pause"
            pause_btn.configure(text=self._l10n.text(key))
            self._on_pause_toggle()

        pause_btn.configure(command=_toggle_pause)
        pause_btn.pack(side=tk.RIGHT)

        def _poll() -> None:
            if self._stop.is_set():
                root.destroy()
                return

            while not self._queue.empty():
                ev = self._queue.get_nowait()
                if isinstance(ev, ProgressUpdated):
                    root.deiconify()
                    title_lbl.configure(text=ev.filename or self._l10n.text("popup.title"))
                    eta_str = _format_eta(ev.eta_seconds)
                    meta_lbl.configure(
                        text=(
                            f"{self._l10n.text('popup.eta', eta=eta_str)}  |  "
                            f"{self._l10n.text('popup.backend', backend=ev.backend_label)}"
                        )
                    )
                    bar["value"] = ev.percent
                    status_lbl.configure(text=f"{ev.percent:.0f}%")
                elif isinstance(ev, (JobCompleted, JobFailed, JobCancelled)):
                    self._paused = False
                    pause_btn.configure(text=self._l10n.text("popup.pause"))
                    root.withdraw()

            root.after(int(TRAY_POLL_INTERVAL_SEC * 1000), _poll)

        root.after(int(TRAY_POLL_INTERVAL_SEC * 1000), _poll)
        root.mainloop()
