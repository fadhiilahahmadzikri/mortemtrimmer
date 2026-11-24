"""Shared PyQt6 theme and single-instance QLocalServer launcher helpers."""

from __future__ import annotations

import sys
from collections.abc import Callable

from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMainWindow

from autosilenttrimmer.presentation.theme import (
    PALETTE_ALT_BASE_RGB,
    PALETTE_BASE_RGB,
    PALETTE_BUTTON_RGB,
    PALETTE_HIGHLIGHT_RGB,
    PALETTE_HIGHLIGHT_TEXT_RGB,
    PALETTE_WINDOW_RGB,
    PALETTE_WINDOW_TEXT_RGB,
    build_qt_stylesheet,
    resolve_asset_path,
)


def apply_dark_palette(app: QApplication) -> None:
    """Apply gold-and-warm-brown Mortem Primer theme uniformly across PyQt6 windows."""
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(*PALETTE_WINDOW_RGB))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(*PALETTE_WINDOW_TEXT_RGB))
    pal.setColor(QPalette.ColorRole.Base, QColor(*PALETTE_BASE_RGB))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(*PALETTE_ALT_BASE_RGB))
    pal.setColor(QPalette.ColorRole.Text, QColor(*PALETTE_WINDOW_TEXT_RGB))
    pal.setColor(QPalette.ColorRole.Button, QColor(*PALETTE_BUTTON_RGB))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(*PALETTE_WINDOW_TEXT_RGB))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(*PALETTE_HIGHLIGHT_RGB))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(*PALETTE_HIGHLIGHT_TEXT_RGB))
    app.setPalette(pal)
    app.setStyleSheet(build_qt_stylesheet())

    icon_path = resolve_asset_path("mortem_icon.png")
    if icon_path is not None:
        app.setWindowIcon(QIcon(icon_path))


def run_single_instance_window(ipc_name: str, window_factory: Callable[[], QMainWindow]) -> int:
    """Show a PyQt6 window once, raising an already-open instance via local IPC."""
    app = QApplication.instance() or QApplication(sys.argv[:1])
    assert isinstance(app, QApplication)
    apply_dark_palette(app)

    probe_sock = QLocalSocket()
    probe_sock.connectToServer(ipc_name)
    if probe_sock.waitForConnected(150):
        probe_sock.write(b"raise")
        probe_sock.flush()
        probe_sock.waitForBytesWritten(150)
        probe_sock.disconnectFromServer()
        return 0

    QLocalServer.removeServer(ipc_name)
    server = QLocalServer(app)
    server.listen(ipc_name)

    window = window_factory()

    def _on_new_conn() -> None:
        conn = server.nextPendingConnection()
        if conn is not None:
            conn.close()
        window.showNormal()
        window.raise_()
        window.activateWindow()

    server.newConnection.connect(_on_new_conn)
    window.show()
    try:
        return app.exec()
    finally:
        server.close()
