# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Standalone single-instance PyQt6 About window launcher (--about)."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from autosilenttrimmer.presentation.about_dialog import AboutDialog
from autosilenttrimmer.presentation.qt_app import apply_dark_palette


def run_about_ui() -> int:
    """Open Mortem Trimmer About dialog as standalone GUI entrypoint."""
    app = QApplication.instance() or QApplication(sys.argv[:1])
    assert isinstance(app, QApplication)
    apply_dark_palette(app)
    dialog = AboutDialog()
    dialog.exec()
    return 0
