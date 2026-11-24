"""Single-instance Qt application launcher for the Tune configuration UI."""

from __future__ import annotations

import logging
import sys

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration
from autosilenttrimmer.domain.contracts.storage import ISettingsRepository
from autosilenttrimmer.presentation.tune.tune_window import TuneWindow

logger = logging.getLogger(__name__)

_TUNE_IPC_NAME = "autosilenttrimmer_tune_ui"


def _apply_dark_palette(app: QApplication) -> None:
    """Apply crisp minimal dark Fusion palette without overriding OS layouts heavily."""
    from PyQt6.QtGui import QColor, QPalette

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


def run_tune_ui(
    *,
    settings_repo: ISettingsRepository,
    settings_file_path: str,
    gateway_client: IJobGatewayClient | None = None,
    shell_integration: IShellIntegration | None = None,
    shim_executable_path: str | None = None,
) -> int:
    """Launch PyQt6 Tune configuration window enforcing single UI instance."""
    app = QApplication.instance() or QApplication(sys.argv[:1])
    assert isinstance(app, QApplication)
    _apply_dark_palette(app)

    # Single-instance check: raise existing Tune window instead of duplicating
    probe_sock = QLocalSocket()
    probe_sock.connectToServer(_TUNE_IPC_NAME)
    if probe_sock.waitForConnected(150):
        probe_sock.write(b"raise")
        probe_sock.flush()
        probe_sock.waitForBytesWritten(150)
        probe_sock.disconnectFromServer()
        return 0

    QLocalServer.removeServer(_TUNE_IPC_NAME)
    server = QLocalServer(app)
    server.listen(_TUNE_IPC_NAME)

    window = TuneWindow(
        settings_repo=settings_repo,
        settings_file_path=settings_file_path,
        gateway_client=gateway_client,
        shell_integration=shell_integration,
        shim_executable_path=shim_executable_path,
    )

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
