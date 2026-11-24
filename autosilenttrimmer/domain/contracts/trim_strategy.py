# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Pluggable trim strategy contract (Doc 01 A1, §5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo


class ITrimStrategy(ABC):
    """Abstract trim strategy producing keep-segments from analyzed media."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique strategy identifier (e.g. 'auto-silence', 'manual-range')."""
        pass

    @property
    @abstractmethod
    def requires_frame_accuracy(self) -> bool:
        """Whether strategy outputs sub-GOP boundaries needing SMART_CUT/REENCODE."""
        pass

    @abstractmethod
    def plan_keep_segments(
        self,
        probe_info: MediaProbeInfo,
        audio_path: str | None = None,
        manifest_path: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[MediaSegment]:
        """Determine media segments to retain cleanly without mutating source."""
        pass
