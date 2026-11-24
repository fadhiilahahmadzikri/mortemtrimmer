# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""FFmpeg locator contract for dynamic executable discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IFFmpegLocator(ABC):
    """Abstract interface for locating an FFmpeg binary executable."""

    @abstractmethod
    def locate(self, explicit_path: str | None = None) -> str:
        """Resolve absolute path to an executable FFmpeg binary."""
        pass
