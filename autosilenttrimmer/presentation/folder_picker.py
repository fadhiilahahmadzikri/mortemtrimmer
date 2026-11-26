# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Native OS folder selection & low-disk destination wizard reusing Qt system file dialogs."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence

from autosilenttrimmer.core.i18n import Localizer


def _format_bytes_human(num_bytes: int) -> str:
    """Format byte counts concisely in MB or GB for disk-space warnings."""
    gb = num_bytes / (1024**3)
    if gb >= 1.0:
        return f"{gb:.2f} GB"
    mb = max(0.0, num_bytes / (1024**2))
    return f"{mb:.1f} MB"


def pick_destination_directory(
    localizer: Localizer,
    *,
    initial_dir: str = "",
    low_disk: bool = False,
    target_path: str = "",
    free_bytes: int = 0,
    required_bytes: int = 0,
) -> str | None:
    """Prompt the user via native OS directory picker; returns selected folder or None."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

    from autosilenttrimmer.presentation.qt_app import apply_dark_palette

    app = QApplication.instance() or QApplication(sys.argv[:1])
    assert isinstance(app, QApplication)
    apply_dark_palette(app)

    host = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
    try:
        if low_disk:
            drive = os.path.splitdrive(os.path.abspath(target_path))[0] or target_path or "C:"
            box = QMessageBox(host)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(localizer.text("dialog.disk_full_title", drive=drive))
            box.setText(
                localizer.text(
                    "dialog.disk_full_body",
                    drive=drive,
                    free_gb=_format_bytes_human(free_bytes),
                    required_gb=_format_bytes_human(required_bytes),
                )
            )
            choose_btn = box.addButton(
                localizer.text("dialog.choose_folder_btn"),
                QMessageBox.ButtonRole.AcceptRole,
            )
            box.addButton(
                localizer.text("dialog.cancel_btn"),
                QMessageBox.ButtonRole.RejectRole,
            )
            box.setDefaultButton(choose_btn)
            box.exec()
            if box.clickedButton() != choose_btn:
                return None

        start_dir = initial_dir if initial_dir and os.path.isdir(initial_dir) else ""
        chosen = QFileDialog.getExistingDirectory(
            host,
            localizer.text("dialog.choose_output_title"),
            start_dir,
        )
        cleaned = (chosen or "").strip()
        return os.path.abspath(cleaned) if cleaned else None
    finally:
        host.close()
        host.deleteLater()


def run_pick_folder_cli(
    localizer: Localizer,
    *,
    initial_dir: str = "",
    reason: str = "normal",
    target_path: str = "",
    free_bytes: int = 0,
    required_bytes: int = 0,
    result_file: str | None = None,
) -> int:
    """CLI entrypoint wrapper running native destination picker cleanly on its own Qt thread."""
    chosen = pick_destination_directory(
        localizer,
        initial_dir=initial_dir,
        low_disk=(reason == "low-disk"),
        target_path=target_path,
        free_bytes=free_bytes,
        required_bytes=required_bytes,
    )
    if not chosen:
        return 1
    if result_file:
        with open(result_file, "w", encoding="utf-8") as fh:
            fh.write(chosen)
    if sys.stdout is not None:
        print(chosen)
    return 0


def prompt_destination_via_subprocess(
    command_prefix: Sequence[str],
    *,
    initial_dir: str = "",
    low_disk: bool = False,
    target_path: str = "",
    free_bytes: int = 0,
    required_bytes: int = 0,
) -> str | None:
    """Launch isolated GUI subprocess so Qt runs on a dedicated main thread from daemon mode."""
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="mortem_dest_",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp_path = tmp.name

        cmd = [
            *command_prefix,
            "--pick-folder",
            "--pick-reason",
            "low-disk" if low_disk else "normal",
            "--initial-dir",
            initial_dir,
            "--pick-result-file",
            tmp_path,
        ]
        if target_path:
            cmd.extend(["--target-path", target_path])
        if free_bytes > 0:
            cmd.extend(["--free-bytes", str(free_bytes)])
        if required_bytes > 0:
            cmd.extend(["--required-bytes", str(required_bytes)])

        kwargs: dict[str, object] = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, **kwargs)  # type: ignore[arg-type]
        if proc.returncode != 0 or not tmp_path or not os.path.isfile(tmp_path):
            return None
        with open(tmp_path, encoding="utf-8") as fh:
            picked = fh.read().strip()
        return os.path.abspath(picked) if picked else None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
