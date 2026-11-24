"""Single-instance Qt launcher for the read-only System Logs & Activity viewer."""

from __future__ import annotations

from collections.abc import Callable

from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.presentation.logs.log_viewer import LogViewerWindow
from autosilenttrimmer.presentation.qt_app import run_single_instance_window

_LOGS_IPC_NAME = "autosilenttrimmer_logs_ui"


def run_logs_ui(
    *,
    log_file_path: str,
    gateway_client: IJobGatewayClient | None = None,
    on_open_tune: Callable[[], None] | None = None,
) -> int:
    """Launch PyQt6 read-only System Log Viewer enforcing a single window instance."""
    return run_single_instance_window(
        _LOGS_IPC_NAME,
        lambda: LogViewerWindow(
            log_file_path=log_file_path,
            gateway_client=gateway_client,
            on_open_tune=on_open_tune,
        ),
    )
