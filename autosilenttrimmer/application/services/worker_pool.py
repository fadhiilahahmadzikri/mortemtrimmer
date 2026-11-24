# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Adaptive parallel chunk Worker Pool with per-chunk retry and G2 GPU->CPU fallback."""

from __future__ import annotations

import os
import shutil
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from autosilenttrimmer.core.constants import (
    APP_NAME,
    ETA_SMOOTHING_ALPHA,
    TEMP_AUDIO_SUFFIX,
    TEMP_VIDEO_SUFFIX,
    VIDEO_CODEC_LIBX264,
)
from autosilenttrimmer.core.exceptions import ChunkProcessingException, ErrorCode
from autosilenttrimmer.domain.contracts.compute import IComputeBackend
from autosilenttrimmer.domain.contracts.event_bus import IEventBus
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.notifier import INotifier
from autosilenttrimmer.domain.entities.job import ChunkStatus, ChunkTask, Job
from autosilenttrimmer.domain.models.compute import BackendSelection
from autosilenttrimmer.domain.models.events import (
    BackendFallback,
    ChunkCompleted,
    ProgressUpdated,
)
from autosilenttrimmer.domain.models.media_probe import ExecutionMode, MediaProbeInfo


class ChunkWorkerPool:
    """Executes chunk processing across parallel workers with G2 CPU fallback recovery."""

    def __init__(
        self,
        *,
        media_manager: IMediaManager,
        compute_backend: IComputeBackend,
        event_bus: IEventBus,
        notifier: INotifier | None = None,
        max_retries: int = 2,
    ) -> None:
        self._media_manager = media_manager
        self._compute_backend = compute_backend
        self._bus = event_bus
        self._notifier = notifier
        self._max_retries = max_retries

    def execute_chunks(
        self,
        *,
        job: Job,
        probe: MediaProbeInfo,
        plan_chunks: list,
        worker_count: int,
        mode: ExecutionMode,
        backend: BackendSelection,
        work_dir: str,
        t_start: float,
        check_controls: Callable[[Job], None],
        persist_job: Callable[[Job], None],
    ) -> tuple[list[str], BackendSelection]:
        """Execute planned chunks in parallel, returning ordered output file paths."""
        chunk_ext = TEMP_VIDEO_SUFFIX if probe.is_video else TEMP_AUDIO_SUFFIX
        if not plan_chunks:
            fallback_copy = os.path.join(work_dir, f"full{chunk_ext}")
            shutil.copyfile(job.source_path, fallback_copy)
            return [fallback_copy], backend

        job.chunks = [
            ChunkTask(
                index=cp.index,
                start_sec=cp.start_sec,
                end_sec=cp.end_sec,
                segments=list(cp.keep_segments),
                output_path=os.path.join(work_dir, f"chunk_{cp.index:04d}{chunk_ext}"),
            )
            for cp in plan_chunks
        ]
        persist_job(job)

        active_backend = backend
        ema_eta: float | None = None
        lock = threading.Lock()

        def _run_chunk(task: ChunkTask) -> str:
            nonlocal active_backend
            check_controls(job)
            assert task.output_path is not None
            max_attempts = max(1, self._max_retries + 1)

            for attempt in range(max_attempts):
                check_controls(job)
                task.status = ChunkStatus.RUNNING
                t0 = time.monotonic()
                try:
                    with lock:
                        encoder = active_backend.video_encoder
                    self._media_manager.slice_and_concat(
                        media_path=job.source_path,
                        segments=task.segments,
                        output_path=task.output_path,
                        video_encoder=encoder,
                        copy_mode=(mode == ExecutionMode.COPY),
                    )
                    task.status = ChunkStatus.COMPLETED
                    self._bus.publish(
                        ChunkCompleted(
                            job_id=job.job_id,
                            chunk_index=task.index,
                            total_chunks=len(job.chunks),
                            duration_ms=(time.monotonic() - t0) * 1000.0,
                        )
                    )
                    persist_job(job)
                    return task.output_path
                except Exception as exc:
                    task.retries = attempt + 1
                    task.error_message = str(exc)
                    with lock:
                        if (
                            active_backend.is_gpu
                            and active_backend.video_encoder != VIDEO_CODEC_LIBX264
                        ):
                            prev = active_backend.backend_id
                            active_backend = self._compute_backend.fallback_to_cpu(str(exc))
                            self._bus.publish(
                                BackendFallback(
                                    job_id=job.job_id,
                                    from_backend=prev,
                                    to_backend=active_backend.backend_id,
                                    reason=str(exc),
                                )
                            )
                            if self._notifier:
                                self._notifier.notify_info(APP_NAME, f"GPU fallback -> CPU ({exc})")

            task.status = ChunkStatus.FAILED
            raise ChunkProcessingException(
                f"Chunk {task.index} failed after retries: {task.error_message}",
                code=ErrorCode.CHUNK_FAILED,
            )

        results: dict[int, str] = {}
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = {pool.submit(_run_chunk, t): t for t in job.chunks}
            for fut in as_completed(futures):
                task = futures[fut]
                results[task.index] = fut.result()
                ema_eta = self.emit_progress(
                    self._bus, job, active_backend.backend_id, t_start, ema_eta
                )

        return [results[i] for i in sorted(results)], active_backend

    @staticmethod
    def emit_progress(
        bus: IEventBus,
        job: Job,
        backend_id: str,
        t_start: float,
        prev_eta: float | None = None,
    ) -> float | None:
        """Compute smoothed ETA and emit duration-weighted ProgressUpdated event."""
        pct = job.progress_percent
        eta: float | None = None
        elapsed = max(0.1, time.monotonic() - t_start)
        if 5.0 < pct < 100.0:
            raw_eta = elapsed * ((100.0 - pct) / pct)
            eta = (
                raw_eta
                if prev_eta is None
                else (ETA_SMOOTHING_ALPHA * raw_eta) + ((1.0 - ETA_SMOOTHING_ALPHA) * prev_eta)
            )
        bus.publish(
            ProgressUpdated(
                job_id=job.job_id,
                filename=os.path.basename(job.source_path),
                percent=pct,
                eta_seconds=eta,
                backend_label=backend_id.upper(),
            )
        )
        return eta
