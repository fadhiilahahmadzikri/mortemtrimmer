# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""OS Explorer/Finder/File-Manager shell context menu integration contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IShellIntegration(ABC):
    """Cross-platform port registering right-click 'Trim This Video' shell menu."""

    @abstractmethod
    def register(self, executable_path: str, label: str, extensions: frozenset[str]) -> None:
        """Register per-user shell context menu entry pointing to thin shim executable."""
        pass

    @abstractmethod
    def unregister(self, extensions: frozenset[str]) -> None:
        """Cleanly remove shell entries leaving zero orphaned menu items."""
        pass

    @abstractmethod
    def is_registered(self, extensions: frozenset[str]) -> bool:
        """Check whether context menu integration is active for target extensions."""
        pass
