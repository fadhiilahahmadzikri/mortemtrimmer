# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Media probing, execution planning, and chunk planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from autosilenttrimmer.domain.entities.segment import MediaSegment


class ExecutionMode(StrEnum):
    """Execution precision/speed mode selected by ExecutionPlanner (Doc 01 §7.1)."""

    COPY = "COPY"
    SMART_CUT = "SMART_CUT"
    REENCODE = "REENCODE"
    ANALYZE = "ANALYZE"


@dataclass(frozen=True)
class StreamSummary:
    """Single stream metadata returned by IMediaProber."""

    index: int
    media_type: str  # "video" | "audio" | "subtitle"
    codec_name: str
    sample_rate: int | None = None
    channels: int | None = None
    width: int | None = None
    height: int | None = None
    bit_rate: int | None = None


@dataclass(frozen=True)
class MediaProbeInfo:
    """Comprehensive container and stream characteristics from IMediaProber."""

    path: str
    container_format: str
    extension: str
    duration_sec: float
    file_size_bytes: int
    is_video: bool
    is_vfr: bool = False
    rotation_degrees: int = 0
    is_hdr: bool = False
    video_streams: tuple[StreamSummary, ...] = field(default_factory=tuple)
    audio_streams: tuple[StreamSummary, ...] = field(default_factory=tuple)
    subtitle_streams: tuple[StreamSummary, ...] = field(default_factory=tuple)
    keyframe_timestamps: tuple[float, ...] = field(default_factory=tuple)

    @property
    def is_seekable(self) -> bool:
        """Container is seekable when duration is positive and audio/video exists."""
        return self.duration_sec > 0.0 and (
            len(self.video_streams) > 0 or len(self.audio_streams) > 0
        )


@dataclass(frozen=True)
class ChunkPlan:
    """Immutable descriptor of a single chunk to be executed by WorkerPool."""

    index: int
    start_sec: float
    end_sec: float
    keep_segments: tuple[MediaSegment, ...]


@dataclass(frozen=True)
class ProcessingPlan:
    """Compiled execution blueprint bridging Planner -> WorkerPool -> Merger."""

    mode: ExecutionMode
    worker_count: int
    video_encoder: str
    chunks: tuple[ChunkPlan, ...]
    keep_segments: tuple[MediaSegment, ...]
    estimated_temp_bytes: int
