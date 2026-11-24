# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Single-instance Qt application launcher for the Tune configuration UI."""

from __future__ import annotations

from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration
from autosilenttrimmer.domain.contracts.storage import ISettingsRepository
from autosilenttrimmer.presentation.qt_app import run_single_instance_window
from autosilenttrimmer.presentation.tune.tune_window import TuneWindow

_TUNE_IPC_NAME = "autosilenttrimmer_tune_ui"


def run_tune_ui(
    *,
    settings_repo: ISettingsRepository,
    settings_file_path: str,
    gateway_client: IJobGatewayClient | None = None,
    shell_integration: IShellIntegration | None = None,
    shim_executable_path: str | None = None,
) -> int:
    """Launch PyQt6 Tune configuration window enforcing single UI instance."""
    return run_single_instance_window(
        _TUNE_IPC_NAME,
        lambda: TuneWindow(
            settings_repo=settings_repo,
            settings_file_path=settings_file_path,
            gateway_client=gateway_client,
            shell_integration=shell_integration,
            shim_executable_path=shim_executable_path,
        ),
    )
