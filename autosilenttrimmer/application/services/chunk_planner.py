"""Keyframe-aligned adaptive chunk planner (Doc 01 §7.3)."""

from __future__ import annotations

import bisect

from autosilenttrimmer.core.constants import (
    MIN_CHUNKABLE_DURATION_SEC,
    TARGET_CHUNK_MAX_SEC,
    TARGET_CHUNK_MIN_SEC,
)
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.media_probe import ChunkPlan, ExecutionMode, MediaProbeInfo


class ChunkPlanner:
    """Partitions kept speech segments cleanly into keyframe-aligned parallel chunks."""

    def __init__(
        self,
        chunk_min_sec: float = TARGET_CHUNK_MIN_SEC,
        chunk_max_sec: float = TARGET_CHUNK_MAX_SEC,
    ) -> None:
        self._chunk_min_sec = chunk_min_sec
        self._chunk_max_sec = chunk_max_sec

    def plan_chunks(
        self,
        probe_info: MediaProbeInfo,
        keep_segments: list[MediaSegment],
        mode: ExecutionMode,
        worker_count: int,
    ) -> list[ChunkPlan]:
        """Split or batch segments into keyframe-safe parallel ChunkPlans."""
        if not keep_segments:
            return []

        total_keep = sum(s.duration for s in keep_segments)
        if (
            worker_count <= 1
            or mode == ExecutionMode.COPY
            or total_keep < MIN_CHUNKABLE_DURATION_SEC
        ):
            return [
                ChunkPlan(
                    index=0,
                    start_sec=keep_segments[0].start,
                    end_sec=keep_segments[-1].end,
                    keep_segments=tuple(keep_segments),
                )
            ]

        desired_chunks = max(worker_count * 2, 2)
        target_span = min(
            self._chunk_max_sec,
            max(self._chunk_min_sec, total_keep / desired_chunks),
        )

        normalized_segments = self._split_long_segments(
            keep_segments, target_span, probe_info.keyframe_timestamps
        )

        plans: list[ChunkPlan] = []
        current_batch: list[MediaSegment] = []
        accumulated = 0.0

        for seg in normalized_segments:
            current_batch.append(seg)
            accumulated += seg.duration
            if accumulated >= target_span:
                plans.append(
                    ChunkPlan(
                        index=len(plans),
                        start_sec=current_batch[0].start,
                        end_sec=current_batch[-1].end,
                        keep_segments=tuple(current_batch),
                    )
                )
                current_batch = []
                accumulated = 0.0

        if current_batch:
            plans.append(
                ChunkPlan(
                    index=len(plans),
                    start_sec=current_batch[0].start,
                    end_sec=current_batch[-1].end,
                    keep_segments=tuple(current_batch),
                )
            )

        return plans

    def _split_long_segments(
        self,
        segments: list[MediaSegment],
        target_span: float,
        keyframes: tuple[float, ...],
    ) -> list[MediaSegment]:
        """Split single segments exceeding max chunk size along nearest keyframes."""
        result: list[MediaSegment] = []
        max_len = max(self._chunk_max_sec, target_span)

        for seg in segments:
            if seg.duration <= max_len:
                result.append(seg)
                continue

            cursor = seg.start
            while seg.end - cursor > max_len:
                ideal_cut = cursor + target_span
                cut_point = self._nearest_keyframe(
                    ideal_cut, cursor + 5.0, seg.end - 5.0, keyframes
                )
                if cut_point <= cursor or cut_point >= seg.end:
                    cut_point = ideal_cut
                result.append(MediaSegment(start=cursor, end=cut_point))
                cursor = cut_point

            if cursor < seg.end:
                result.append(MediaSegment(start=cursor, end=seg.end))

        return result

    @staticmethod
    def _nearest_keyframe(
        target: float,
        lower_bound: float,
        upper_bound: float,
        keyframes: tuple[float, ...],
    ) -> float:
        """Select nearest keyframe inside [lower_bound, upper_bound] or return target."""
        if not keyframes:
            return target
        idx = bisect.bisect_left(keyframes, target)
        candidates: list[float] = []
        if idx > 0:
            candidates.append(keyframes[idx - 1])
        if idx < len(keyframes):
            candidates.append(keyframes[idx])
        valid = [k for k in candidates if lower_bound <= k <= upper_bound]
        if not valid:
            return target
        return min(valid, key=lambda k: abs(k - target))
