# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Platform shell integration factory and future macOS/Linux stubs."""

from __future__ import annotations

import logging
import os

from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration

logger = logging.getLogger(__name__)


class StubShellIntegrationAdapter(IShellIntegration):
    """Cross-platform placeholder contract for macOS Finder / Linux Desktop menus."""

    def __init__(self, platform_name: str) -> None:
        self._platform_name = platform_name

    def register(self, executable_path: str, label: str, extensions: frozenset[str]) -> None:
        logger.warning(
            "Shell context menu registration is planned for '%s' in future release.",
            self._platform_name,
        )

    def unregister(self, extensions: frozenset[str]) -> None:
        logger.debug("No shell entries to clean on '%s'.", self._platform_name)

    def is_registered(self, extensions: frozenset[str]) -> bool:
        return False


def create_shell_integration() -> IShellIntegration:
    """Resolve active OS shell integration adapter."""
    if os.name == "nt":
        from autosilenttrimmer.infrastructure.platform.shell.windows_registry import (
            WindowsRegistryShellAdapter,
        )

        return WindowsRegistryShellAdapter()
    import platform

    return StubShellIntegrationAdapter(platform.system())
