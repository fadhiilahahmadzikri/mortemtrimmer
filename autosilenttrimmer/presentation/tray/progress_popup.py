"""Lightweight gold-and-warm-brown Tkinter progress overlay popup for Mortem Primer."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections.abc import Callable

from autosilenttrimmer.core.constants import TRAY_POLL_INTERVAL_SEC
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.models.events import (
    DomainEvent,
    JobCancelled,
    JobCompleted,
    JobFailed,
    JobQueued,
    JobStarted,
    ProgressUpdated,
)
from autosilenttrimmer.presentation.theme import (
    ACCENT_GOLD,
    ACCENT_GOLD_BRIGHT,
    BG_BASE,
    BG_DEEP,
    BG_ELEVATED,
    BORDER_STRONG,
    BORDER_SUBTLE,
    STATUS_ERROR,
    STATUS_ERROR_BG,
    STATUS_ERROR_TEXT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_error_code_label,
    format_stage_label,
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
    """Thread-safe unobtrusive bottom-right progress overlay without a heavy main window."""

    def __init__(
        self,
        localizer: Localizer,
        *,
        on_pause_toggle: Callable[[], None],
        on_cancel: Callable[[], None],
        on_open_logs: Callable[[], None] | None = None,
    ) -> None:
        self._l10n = localizer
        self._on_pause_toggle = on_pause_toggle
        self._on_cancel = on_cancel
        self._on_open_logs = on_open_logs
        self._queue: queue.Queue[DomainEvent] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._paused = False

    def push_event(self, event: DomainEvent) -> None:
        """Queue domain progress and terminal events safely from any worker thread."""
        self._queue.put(event)

    def start(self) -> None:
        """Start UI widget thread cleanly; becomes no-op if display is unavailable."""
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
        root.configure(bg=BG_BASE)

        width, height = 400, 152
        scr_w = root.winfo_screenwidth()
        scr_h = root.winfo_screenheight()
        root.geometry(f"{width}x{height}+{scr_w - width - 20}+{scr_h - height - 60}")
        root.withdraw()

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(
            "Mortem.Horizontal.TProgressbar",
            troughcolor=BG_DEEP,
            background=ACCENT_GOLD,
            bordercolor=BORDER_SUBTLE,
            lightcolor=ACCENT_GOLD_BRIGHT,
            darkcolor=BORDER_STRONG,
            thickness=8,
        )

        frame = tk.Frame(
            root,
            bg=BG_BASE,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER_STRONG,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        title_lbl = tk.Label(
            frame,
            text=self._l10n.text("popup.title"),
            fg=TEXT_PRIMARY,
            bg=BG_BASE,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        title_lbl.pack(fill=tk.X)

        meta_lbl = tk.Label(
            frame,
            text="",
            fg=TEXT_SECONDARY,
            bg=BG_BASE,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=366,
        )
        meta_lbl.pack(fill=tk.X, pady=(3, 8))

        bar = ttk.Progressbar(
            frame,
            mode="determinate",
            maximum=100.0,
            style="Mortem.Horizontal.TProgressbar",
        )
        bar.pack(fill=tk.X, pady=(0, 10))

        btn_row = tk.Frame(frame, bg=BG_BASE)
        btn_row.pack(fill=tk.X)

        status_lbl = tk.Label(
            btn_row,
            text="0%",
            fg=ACCENT_GOLD_BRIGHT,
            bg=BG_BASE,
            font=("Segoe UI", 9, "bold"),
        )
        status_lbl.pack(side=tk.LEFT)

        def _dismiss_or_cancel() -> None:
            if error_hide_at[0] > 0.0:
                error_hide_at[0] = 0.0
                root.withdraw()
            else:
                self._on_cancel()

        cancel_btn = tk.Button(
            btn_row,
            text=self._l10n.text("popup.cancel"),
            command=_dismiss_or_cancel,
            bg=STATUS_ERROR_BG,
            fg=STATUS_ERROR_TEXT,
            activebackground=BORDER_STRONG,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=2,
            font=("Segoe UI", 8),
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        logs_btn = tk.Button(
            btn_row,
            text=self._l10n.text("popup.logs"),
            command=lambda: self._on_open_logs() if self._on_open_logs else None,
            bg=BG_ELEVATED,
            fg=ACCENT_GOLD_BRIGHT,
            activebackground=BORDER_STRONG,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=2,
            font=("Segoe UI", 8),
        )
        if self._on_open_logs is not None:
            logs_btn.pack(side=tk.RIGHT, padx=(6, 0))

        pause_btn = tk.Button(
            btn_row,
            text=self._l10n.text("popup.pause"),
            bg=BG_ELEVATED,
            fg=TEXT_PRIMARY,
            activebackground=BORDER_STRONG,
            activeforeground=TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=2,
            font=("Segoe UI", 8),
        )

        error_hide_at: list[float] = [0.0]

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

            if error_hide_at[0] > 0.0 and time.monotonic() >= error_hide_at[0]:
                error_hide_at[0] = 0.0
                root.withdraw()

            while not self._queue.empty():
                ev = self._queue.get_nowait()
                if isinstance(ev, (JobQueued, JobStarted)):
                    error_hide_at[0] = 0.0
                    root.deiconify()
                    root.lift()
                    title_lbl.configure(
                        text=os.path.basename(ev.source_path) or self._l10n.text("popup.title")
                    )
                    stage_name = format_stage_label(
                        "QUEUED" if isinstance(ev, JobQueued) else "STARTING"
                    )
                    meta_lbl.configure(
                        text=self._l10n.text("popup.queued", stage=stage_name),
                        fg=TEXT_SECONDARY,
                    )
                    bar["value"] = 2.0
                    status_lbl.configure(text="2%", fg=ACCENT_GOLD_BRIGHT)
                    cancel_btn.configure(text=self._l10n.text("popup.cancel"))
                elif isinstance(ev, ProgressUpdated):
                    error_hide_at[0] = 0.0
                    root.deiconify()
                    root.lift()
                    title_lbl.configure(text=ev.filename or self._l10n.text("popup.title"))
                    clean_label = format_stage_label(ev.backend_label)
                    if ev.eta_seconds is None:
                        meta_text = self._l10n.text("popup.stage", stage=clean_label)
                    else:
                        eta_str = _format_eta(ev.eta_seconds)
                        meta_text = (
                            f"{self._l10n.text('popup.eta', eta=eta_str)}  |  "
                            f"{self._l10n.text('popup.backend', backend=clean_label)}"
                        )
                    meta_lbl.configure(text=meta_text, fg=TEXT_SECONDARY)
                    bar["value"] = ev.percent
                    status_lbl.configure(text=f"{ev.percent:.0f}%", fg=ACCENT_GOLD_BRIGHT)
                    cancel_btn.configure(text=self._l10n.text("popup.cancel"))
                elif isinstance(ev, JobFailed):
                    self._paused = False
                    pause_btn.configure(text=self._l10n.text("popup.pause"))
                    root.deiconify()
                    root.lift()
                    title_lbl.configure(
                        text=os.path.basename(ev.source_path) or self._l10n.text("popup.title")
                    )
                    short_msg = (ev.message or "")[:120]
                    meta_lbl.configure(
                        text=self._l10n.text(
                            "popup.failed",
                            code=format_error_code_label(ev.error_code or ""),
                            message=short_msg,
                        ),
                        fg=STATUS_ERROR_TEXT,
                    )
                    status_lbl.configure(text="Failed", fg=STATUS_ERROR)
                    cancel_btn.configure(text=self._l10n.text("popup.dismiss"))
                    error_hide_at[0] = time.monotonic() + 25.0
                elif isinstance(ev, (JobCompleted, JobCancelled)):
                    self._paused = False
                    error_hide_at[0] = 0.0
                    pause_btn.configure(text=self._l10n.text("popup.pause"))
                    root.withdraw()

            root.after(int(TRAY_POLL_INTERVAL_SEC * 1000), _poll)

        root.after(int(TRAY_POLL_INTERVAL_SEC * 1000), _poll)
        root.mainloop()
