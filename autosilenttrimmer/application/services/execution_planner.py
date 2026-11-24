"""Execution mode and adaptive worker concurrency planner (Doc 01 §7.1, §7.4)."""

from __future__ import annotations

from autosilenttrimmer.application.services.chunk_planner import ChunkPlanner
from autosilenttrimmer.core.config import ExecutionConfig
from autosilenttrimmer.core.constants import (
    DEFAULT_IO_BOUND_CONCURRENCY,
    DEFAULT_RESERVED_CPU_CORES,
    ESTIMATED_MEMORY_PER_WORKER_MB,
    VIDEO_CODEC_COPY,
)
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.compute import BackendSelection, ComputeCapabilities
from autosilenttrimmer.domain.models.media_probe import (
    ExecutionMode,
    MediaProbeInfo,
    ProcessingPlan,
)


class ExecutionPlanner:
    """Computes ExecutionMode, adaptive worker count N, and ProcessingPlan."""

    def __init__(self, chunk_planner: ChunkPlanner | None = None) -> None:
        self._chunk_planner = chunk_planner or ChunkPlanner()

    def build_plan(
        self,
        probe_info: MediaProbeInfo,
        keep_segments: list[MediaSegment],
        capabilities: ComputeCapabilities,
        backend: BackendSelection,
        execution_cfg: ExecutionConfig,
        requires_frame_accuracy: bool = True,
    ) -> ProcessingPlan:
        """Determine execution mode, adaptive worker count N, and keyframe chunks."""
        if probe_info.is_video:
            use_reencode = requires_frame_accuracy and execution_cfg.frame_accurate
            mode = ExecutionMode.REENCODE if use_reencode else ExecutionMode.COPY
            encoder = VIDEO_CODEC_COPY if mode == ExecutionMode.COPY else backend.video_encoder
        else:
            mode = ExecutionMode.REENCODE
            encoder = backend.video_encoder

        worker_count = self.calculate_adaptive_workers(
            capabilities=capabilities,
            backend=backend,
            mode=mode,
            requested_max=execution_cfg.max_workers,
        )

        chunks = self._chunk_planner.plan_chunks(
            probe_info=probe_info,
            keep_segments=keep_segments,
            mode=mode,
            worker_count=worker_count,
        )

        # Estimate temporary storage required across active chunks
        keep_ratio = (
            min(1.0, sum(s.duration for s in keep_segments) / probe_info.duration_sec)
            if probe_info.duration_sec > 0
            else 1.0
        )
        est_temp = int(probe_info.file_size_bytes * max(0.25, keep_ratio) * 1.5)

        return ProcessingPlan(
            mode=mode,
            worker_count=worker_count,
            video_encoder=encoder,
            chunks=tuple(chunks),
            keep_segments=tuple(keep_segments),
            estimated_temp_bytes=est_temp,
        )

    @staticmethod
    def calculate_adaptive_workers(
        capabilities: ComputeCapabilities,
        backend: BackendSelection,
        mode: ExecutionMode,
        requested_max: int | None = None,
    ) -> int:
        """Implement Doc 01 §7.4 bounded worker formula."""
        cpu_budget = max(1, capabilities.logical_cores - DEFAULT_RESERVED_CPU_CORES)
        available_mb = max(
            ESTIMATED_MEMORY_PER_WORKER_MB,
            capabilities.available_ram_bytes // (1024 * 1024),
        )
        mem_budget = max(1, available_mb // ESTIMATED_MEMORY_PER_WORKER_MB)
        io_cap = DEFAULT_IO_BOUND_CONCURRENCY if mode == ExecutionMode.COPY else cpu_budget

        optimal = min(cpu_budget, mem_budget, max(1, backend.max_concurrency), io_cap)
        if requested_max is not None and requested_max > 0:
            optimal = min(optimal, requested_max)
        return max(1, optimal)
