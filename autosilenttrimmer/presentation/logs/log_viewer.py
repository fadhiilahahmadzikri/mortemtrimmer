"""Strict read-only PyQt6 system log & activity viewer retaining full log history."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from autosilenttrimmer.core.constants import APP_NAME
from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.presentation.theme import (
    STATUS_ERROR_BG,
    STATUS_ERROR_TEXT,
    STATUS_OK,
    STATUS_WARN,
    TEXT_SECONDARY,
    resolve_asset_path,
)

_LOG_LEVEL_OPTIONS: tuple[tuple[str, str], ...] = (
    ("All Levels", "ALL"),
    ("Errors", "ERROR"),
    ("Warnings", "WARNING"),
    ("Info", "INFO"),
)


def _open_folder_in_os(dir_path: str) -> None:
    abs_dir = os.path.abspath(dir_path)
    if not os.path.isdir(abs_dir):
        return
    if os.name == "nt":
        os.startfile(abs_dir)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", abs_dir])
    else:
        subprocess.Popen(["xdg-open", abs_dir])


def read_preserved_log_lines(log_file_path: str) -> list[str]:
    """Read preserved append-only log lines without ever modifying or truncating the file."""
    if not os.path.isfile(log_file_path):
        return []
    with open(log_file_path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def filter_log_lines(lines: list[str], level_filter: str, query: str) -> list[str]:
    """Filter preserved log entries non-destructively in memory for inspection."""
    q = query.strip().lower()
    lvl = level_filter.upper()
    matched: list[str] = []
    for line in lines:
        if lvl == "ERROR" and "[ERROR]" not in line and "[CRITICAL]" not in line:
            continue
        if lvl == "WARNING" and "[WARNING]" not in line and "[ERROR]" not in line:
            continue
        if lvl == "INFO" and "[INFO]" not in line:
            continue
        if q and q not in line.lower():
            continue
        matched.append(line)
    return matched


class LogViewerWindow(QMainWindow):
    """Non-destructive system log & daemon activity inspector."""

    def __init__(
        self,
        *,
        log_file_path: str,
        gateway_client: IJobGatewayClient | None = None,
        on_open_tune: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._log_path = log_file_path
        self._gateway = gateway_client
        self._on_open_tune = on_open_tune
        self._last_size = -1
        self._last_mtime = -1.0
        self._all_lines: list[str] = []

        self.setWindowTitle(f"System Logs — {APP_NAME}")
        self.resize(940, 620)
        self.setMinimumSize(700, 440)

        self._build_ui()
        self.refresh_logs(force=True)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_poll_timer)
        self._timer.start()

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        # Header & Daemon/Error summary
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        icon_path = resolve_asset_path("mortem_icon.png")
        if icon_path is not None:
            emblem = QLabel(self)
            emblem.setPixmap(
                QPixmap(icon_path).scaled(
                    24,
                    24,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            top_row.addWidget(emblem)

        title_lbl = QLabel(f"{APP_NAME} System Logs", self)
        title_lbl.setObjectName("headerTitle")
        self._daemon_lbl = QLabel("Background Service: Checking...", self)
        self._daemon_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(title_lbl)
        top_row.addStretch(1)
        top_row.addWidget(self._daemon_lbl)
        root.addLayout(top_row)

        self._meta_lbl = QLabel(f"History preserved automatically  •  {self._log_path}", self)
        self._meta_lbl.setObjectName("headerSubtitle")
        self._meta_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        root.addWidget(self._meta_lbl)

        self._error_banner = QLabel("No recorded errors.", self)
        self._error_banner.setWordWrap(True)
        root.addWidget(self._error_banner)

        # Filter controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)
        self._level_combo = QComboBox(self)
        for display_text, level_key in _LOG_LEVEL_OPTIONS:
            self._level_combo.addItem(display_text, level_key)
        self._level_combo.currentIndexChanged.connect(lambda _idx: self._render_filtered())

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Filter by filename, job ID, or message...")
        self._search_edit.textChanged.connect(lambda _t: self._render_filtered())

        self._auto_refresh_cb = QCheckBox("Live Refresh (1s)", self)
        self._auto_refresh_cb.setChecked(True)
        self._auto_scroll_cb = QCheckBox("Auto-Scroll", self)
        self._auto_scroll_cb.setChecked(True)

        ctrl_row.addWidget(QLabel("Level:", self))
        ctrl_row.addWidget(self._level_combo)
        ctrl_row.addWidget(self._search_edit, stretch=1)
        ctrl_row.addWidget(self._auto_refresh_cb)
        ctrl_row.addWidget(self._auto_scroll_cb)
        root.addLayout(ctrl_row)

        # Read-only log viewport
        self._text_view = QPlainTextEdit(self)
        self._text_view.setReadOnly(True)
        self._text_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text_view.setFont(font)
        root.addWidget(self._text_view, stretch=1)

        # Footer action bar (intentionally read-only: zero truncate/delete actions)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        refresh_btn = QPushButton("Refresh", self)
        folder_btn = QPushButton("Open Folder", self)
        copy_btn = QPushButton("Copy Logs", self)
        close_btn = QPushButton("Close", self)

        refresh_btn.clicked.connect(lambda: self.refresh_logs(force=True))
        folder_btn.clicked.connect(lambda: _open_folder_in_os(os.path.dirname(self._log_path)))
        copy_btn.clicked.connect(self._copy_visible)
        close_btn.clicked.connect(self.close)

        footer.addWidget(refresh_btn)
        footer.addWidget(folder_btn)
        footer.addWidget(copy_btn)
        if self._on_open_tune is not None:
            tune_btn = QPushButton("Open Settings", self)
            tune_btn.clicked.connect(self._on_open_tune)
            footer.addWidget(tune_btn)
        footer.addStretch(1)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _on_poll_timer(self) -> None:
        if self._auto_refresh_cb.isChecked():
            self.refresh_logs(force=False)

    def refresh_logs(self, *, force: bool = False) -> None:
        """Reload log lines if file size or mtime changed without modifying disk logs."""
        self._update_daemon_badge()

        if not os.path.isfile(self._log_path):
            self._all_lines = []
            self._meta_lbl.setText(f"Log file: {self._log_path} (no entries yet)")
            self._error_banner.setText("No recorded errors.")
            self._error_banner.setStyleSheet(f"color: {STATUS_OK}; font-weight: 600;")
            self._text_view.setPlainText("(Waiting for application log entries...)")
            return

        stat = os.stat(self._log_path)
        if not force and stat.st_size == self._last_size and stat.st_mtime == self._last_mtime:
            return

        self._last_size = stat.st_size
        self._last_mtime = stat.st_mtime
        self._all_lines = read_preserved_log_lines(self._log_path)
        size_kb = stat.st_size / 1024.0
        self._meta_lbl.setText(
            f"Log file: {self._log_path}  •  Lines: {len(self._all_lines)}  •  Size: {size_kb:.1f} KB"
        )
        self._update_latest_error_banner()
        self._render_filtered()

    def _update_daemon_badge(self) -> None:
        if self._gateway is None:
            self._daemon_lbl.setText("Background Service: Unavailable")
            self._daemon_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
            return
        running = self._gateway.is_daemon_running()
        if running:
            self._daemon_lbl.setText("Background Service: Running")
            self._daemon_lbl.setStyleSheet(f"color: {STATUS_OK}; font-weight: 600;")
        else:
            self._daemon_lbl.setText("Background Service: Stopped")
            self._daemon_lbl.setStyleSheet(f"color: {STATUS_WARN}; font-weight: 600;")

    def _update_latest_error_banner(self) -> None:
        errors = [ln for ln in self._all_lines if "[ERROR]" in ln or "[CRITICAL]" in ln]
        if errors:
            latest = errors[-1]
            self._error_banner.setText(f"Latest Error ({len(errors)} total): {latest}")
            self._error_banner.setStyleSheet(
                f"background-color: {STATUS_ERROR_BG}; color: {STATUS_ERROR_TEXT}; "
                "border-radius: 5px; padding: 6px 10px; font-weight: 600;"
            )
        else:
            self._error_banner.setText(
                "Status: All quiet — zero errors recorded in preserved logs."
            )
            self._error_banner.setStyleSheet(f"color: {STATUS_OK}; font-weight: 600;")

    def _render_filtered(self) -> None:
        level_key = str(self._level_combo.currentData() or self._level_combo.currentText() or "ALL")
        filtered = filter_log_lines(
            self._all_lines,
            level_key,
            self._search_edit.text(),
        )
        sb = self._text_view.verticalScrollBar()
        prev_pos = sb.value() if sb is not None else 0
        self._text_view.setPlainText("\n".join(filtered))
        if sb is not None:
            if self._auto_scroll_cb.isChecked():
                sb.setValue(sb.maximum())
            else:
                sb.setValue(prev_pos)

    def _copy_visible(self) -> None:
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(self._text_view.toPlainText())

    def closeEvent(self, event: object) -> None:
        self._timer.stop()
        super().closeEvent(event)  # type: ignore[arg-type]
