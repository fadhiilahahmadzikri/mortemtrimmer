"""Shared PyQt6 theme and single-instance QLocalServer launcher helpers."""

from __future__ import annotations

import sys
from collections.abc import Callable

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMainWindow


def apply_dark_palette(app: QApplication) -> None:
    """Apply crisp minimal dark Fusion palette uniformly across desktop windows."""
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(28, 31, 38))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(235, 238, 245))
    pal.setColor(QPalette.ColorRole.Base, QColor(20, 22, 28))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(34, 38, 46))
    pal.setColor(QPalette.ColorRole.Text, QColor(235, 238, 245))
    pal.setColor(QPalette.ColorRole.Button, QColor(42, 46, 56))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(235, 238, 245))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(0, 200, 105))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(12, 14, 18))
    app.setPalette(pal)


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
