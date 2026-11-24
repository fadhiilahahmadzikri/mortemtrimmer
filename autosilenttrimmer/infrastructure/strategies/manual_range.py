# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Manual time-range trim strategy supporting fast keyframe copy or frame-accurate cut."""

from __future__ import annotations

from typing import Any

from autosilenttrimmer.core.exceptions import FormatMismatchException
from autosilenttrimmer.domain.contracts.trim_strategy import ITrimStrategy
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo


class ManualRangeTrimStrategy(ITrimStrategy):
    """Explicit start/end timestamp trim plugin matching Doc 01 A1 extensibility."""

    def __init__(self, frame_accurate: bool = False) -> None:
        self._frame_accurate = frame_accurate

    @property
    def strategy_id(self) -> str:
        return "manual-range"

    @property
    def requires_frame_accuracy(self) -> bool:
        return self._frame_accurate

    def plan_keep_segments(
        self,
        probe_info: MediaProbeInfo,
        audio_path: str | None = None,
        manifest_path: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[MediaSegment]:
        """Parse start_sec and end_sec parameters safely clamped to media duration."""
        cfg = params or {}
        start_sec = float(cfg.get("start_sec", 0.0))
        end_sec = float(cfg.get("end_sec", probe_info.duration_sec))
        clamped_end = (
            min(end_sec, probe_info.duration_sec) if probe_info.duration_sec > 0 else end_sec
        )

        if start_sec < 0.0 or clamped_end <= start_sec:
            raise FormatMismatchException(
                f"Invalid manual trim range [{start_sec}, {clamped_end}] "
                f"for media duration {probe_info.duration_sec:.2f}s."
            )

        return [MediaSegment(start=start_sec, end=clamped_end)]
