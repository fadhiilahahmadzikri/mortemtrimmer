# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Media prober contract for container, codec, keyframe, and VFR inspection."""

from __future__ import annotations

from abc import ABC, abstractmethod

from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo


class IMediaProber(ABC):
    """Abstract interface for inspecting media files prior to planning."""

    @abstractmethod
    def probe(self, media_path: str) -> MediaProbeInfo:
        """Inspect streams, container format, keyframes, VFR status, and rotation."""
        pass
