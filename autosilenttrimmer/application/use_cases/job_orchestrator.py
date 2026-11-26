# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Background Job Orchestrator owning state machine, merge, verify, and notify."""

from __future__ import annotations

import logging
import os
import queue
import shutil
import tempfile
import threading
import time
from collections.abc import Callable

import soundfile as sf

from autosilenttrimmer.application.services.execution_planner import ExecutionPlanner
from autosilenttrimmer.application.services.output_path_resolver import OutputPathResolver
from autosilenttrimmer.application.services.worker_pool import ChunkWorkerPool
from autosilenttrimmer.application.use_cases._job_events import (
    publish_job_completed,
    publish_job_failed,
    publish_stage_transition,
)
from autosilenttrimmer.core.config import MediaProcessingConfig
from autosilenttrimmer.core.constants import (
    MANIFEST_SUFFIX,
    TEMP_AUDIO_SUFFIX,
    TEMP_VIDEO_SUFFIX,
)
from autosilenttrimmer.core.exceptions import (
    AutoSilentTrimmerException,
    ErrorCode,
    FormatMismatchException,
    JobCancelledException,
    MediaVerificationException,
    SourceLockedException,
)
from autosilenttrimmer.domain.contracts.compute import (
    ICapabilityProber,
    IComputeBackend,
    IProcessPriorityController,
)
from autosilenttrimmer.domain.contracts.event_bus import IEventBus
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.media_prober import IMediaProber
from autosilenttrimmer.domain.contracts.media_verifier import IMediaVerifier
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy
from autosilenttrimmer.domain.contracts.notifier import INotifier
from autosilenttrimmer.domain.contracts.storage import IJobManifestRepository
from autosilenttrimmer.domain.contracts.trim_strategy import ITrimStrategy
from autosilenttrimmer.domain.contracts.visualizer import IVisualizer
from autosilenttrimmer.domain.entities.job import Job, JobState
from autosilenttrimmer.domain.models.compute import ComputePolicy
from autosilenttrimmer.domain.models.events import JobCancelled, JobQueued
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo
from autosilenttrimmer.domain.models.processing_command import (
    DestinationPromptRequest,
    ProcessMediaCommand,
)
from autosilenttrimmer.domain.models.processing_result import ProcessingResult

logger = logging.getLogger(__name__)


class JobOrchestrator:
    """Single-owner orchestrator driving Job State Machine, WorkerPool, Merge & Verify."""

    def __init__(
        self,
        *,
        media_manager: IMediaManager,
        media_prober: IMediaProber,
        media_verifier: IMediaVerifier,
        trim_strategy: ITrimStrategy,
        capability_prober: ICapabilityProber,
        compute_backend: IComputeBackend,
        event_bus: IEventBus,
        config: MediaProcessingConfig | None = None,
        noise_reduction: INoiseReductionStrategy | None = None,
        visualizer: IVisualizer | None = None,
        notifier: INotifier | None = None,
        manifest_repo: IJobManifestRepository | None = None,
        priority_ctrl: IProcessPriorityController | None = None,
        on_destination_needed: Callable[[DestinationPromptRequest], str | None] | None = None,
    ) -> None:
        self._media_manager = media_manager
        self._prober = media_prober
        self._verifier = media_verifier
        self._strategy = trim_strategy
        self._cap_prober = capability_prober
        self._compute_backend = compute_backend
        self._bus = event_bus
        self._config = config or MediaProcessingConfig()
        self._noise_reduction = noise_reduction
        self._visualizer = visualizer
        self._notifier = notifier
        self._manifest_repo = manifest_repo
        self._priority_ctrl = priority_ctrl
        self._on_destination_needed = on_destination_needed
        self._planner = ExecutionPlanner()
        self._worker_pool = ChunkWorkerPool(
            media_manager=media_manager,
            compute_backend=compute_backend,
            event_bus=event_bus,
            notifier=notifier,
            max_retries=self._config.execution.chunk_max_retries,
        )

        self._job_queue: queue.Queue[ProcessMediaCommand] = queue.Queue()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel_requested = threading.Event()
        self._stop_worker = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._job_exec_lock = threading.Lock()

    def reconfigure(
        self,
        *,
        config: MediaProcessingConfig,
        media_manager: IMediaManager,
        media_verifier: IMediaVerifier,
        trim_strategy: ITrimStrategy,
        noise_reduction: INoiseReductionStrategy | None = None,
        visualizer: IVisualizer | None = None,
        notifier: INotifier | None = None,
        priority_ctrl: IProcessPriorityController | None = None,
    ) -> None:
        """Atomically apply reloaded UserSettings cleanly between queued jobs."""
        with self._job_exec_lock:
            self._config = config
            self._media_manager = media_manager
            self._verifier = media_verifier
            self._strategy = trim_strategy
            self._noise_reduction = noise_reduction
            self._visualizer = visualizer
            if notifier is not None:
                self._notifier = notifier
            if priority_ctrl is not None:
                self._priority_ctrl = priority_ctrl
            self._worker_pool = ChunkWorkerPool(
                media_manager=media_manager,
                compute_backend=self._compute_backend,
                event_bus=self._bus,
                notifier=self._notifier,
                max_retries=self._config.execution.chunk_max_retries,
            )

    def start_background_worker(self) -> None:
        """Start daemon queue consumer thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self._stop_worker.clear()
        self._worker_thread = threading.Thread(target=self._consume_queue, daemon=True)
        self._worker_thread.start()

    def stop_background_worker(self) -> None:
        """Stop queue consumer gracefully."""
        self._stop_worker.set()
        self._cancel_requested.set()
        self._pause_event.set()

    def enqueue(self, commands: list[ProcessMediaCommand]) -> None:
        """Queue multiple commands atomically into single orchestrator stream."""
        for cmd in commands:
            logger.info("Job queued (strategy=%s): %s", cmd.strategy, cmd.input_path)
            self._job_queue.put(cmd)
            self._bus.publish(JobQueued(job_id="pending", source_path=cmd.input_path))

    def pause(self) -> None:
        """Pause processing before the next chunk execution."""
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume paused execution."""
        self._pause_event.set()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def cancel_current(self) -> None:
        """Signal cooperative cancellation for active job."""
        self._cancel_requested.set()
        self._pause_event.set()

    def _consume_queue(self) -> None:
        while not self._stop_worker.is_set():
            try:
                cmd = self._job_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self.execute_job(cmd)
            except Exception as exc:
                logger.error("Queued job failed for %s: %s", cmd.input_path, exc)
            finally:
                self._job_queue.task_done()

    def execute_job(self, command: ProcessMediaCommand) -> ProcessingResult:
        """Execute deterministic PROBE -> PLAN -> RUN -> MERGE -> VERIFY -> PUBLISH pipeline."""
        with self._job_exec_lock:
            return self._execute_job_locked(command)

    def _execute_job_locked(self, command: ProcessMediaCommand) -> ProcessingResult:
        self._cancel_requested.clear()
        if self._priority_ctrl and self._config.execution.background_priority:
            self._priority_ctrl.apply_background_priority()

        job = Job(source_path=os.path.abspath(command.input_path), strategy=command.strategy)
        staging_path: str | None = None
        temp_work_dir: str | None = None
        t_start = time.monotonic()

        try:
            logger.info(
                "Job %s started (strategy=%s): %s", job.job_id[:8], job.strategy, job.source_path
            )
            probe = self._run_probe_stage(job)
            final_output = OutputPathResolver.resolve_with_disk_guard(
                probe=probe,
                command=command,
                policy=self._config.output_policy,
                on_destination_needed=self._on_destination_needed,
            )
            job.output_path = final_output
            staging_path = OutputPathResolver.make_staging_path(final_output, job.job_id)
            temp_work_dir = tempfile.mkdtemp(
                prefix="trimjob_",
                dir=os.path.dirname(os.path.abspath(final_output)),
            )

            raw_audio = os.path.join(temp_work_dir, f"raw{TEMP_AUDIO_SUFFIX}")
            keep_segments, manifest_path = self._run_plan_stage(
                job, probe, raw_audio, final_output, command
            )

            caps = self._cap_prober.probe()
            backend = self._compute_backend.select_backend(
                policy=ComputePolicy(command.compute_policy),
                ffmpeg_path=self._config.ffmpeg_path or "",
                requested_max_workers=command.max_workers,
            )
            job.backend_id = backend.backend_id
            plan = self._planner.build_plan(
                probe_info=probe,
                keep_segments=keep_segments,
                capabilities=caps,
                backend=backend,
                execution_cfg=self._config.execution,
                requires_frame_accuracy=self._strategy.requires_frame_accuracy,
            )

            self._transition(job, JobState.RUNNING)
            chunk_outputs, active_backend = self._worker_pool.execute_chunks(
                job=job,
                probe=probe,
                plan_chunks=list(plan.chunks),
                worker_count=plan.worker_count,
                mode=plan.mode,
                backend=backend,
                work_dir=temp_work_dir,
                t_start=t_start,
                check_controls=self._check_controls,
                persist_job=self._persist,
            )

            self._transition(job, JobState.MERGING)
            ChunkWorkerPool.emit_progress(self._bus, job, active_backend.backend_id, t_start)
            merged_raw = os.path.join(temp_work_dir, f"merged{_target_temp_ext(probe)}")
            self._merge_and_denoise(
                probe=probe,
                chunk_outputs=chunk_outputs,
                merged_raw=merged_raw,
                staging_path=staging_path,
                work_dir=temp_work_dir,
            )

            self._transition(job, JobState.VERIFYING)
            expected_dur = (
                sum(s.duration for s in keep_segments) if keep_segments else probe.duration_sec
            )
            report = self._verifier.verify(
                output_path=staging_path,
                expected_duration_sec=expected_dur,
                expected_has_video=probe.is_video,
                expected_audio_streams=1 if probe.audio_streams else 0,
            )
            if not report.passed:
                raise MediaVerificationException(
                    report.failure_reason or "Output failed verification.",
                    code=ErrorCode.VERIFY_FAILED,
                )

            self._verify_source_unmodified(job)
            OutputPathResolver.atomic_publish(staging_path, final_output)
            staging_path = None
            self._transition(job, JobState.DONE)

            plot_path: str | None = None
            if self._visualizer and self._config.ui.generate_visual_artifacts and keep_segments:
                plot_path = self._visualizer.generate_timeline_plot(
                    keep_segments, probe.duration_sec, final_output
                )

            silence_removed = max(0.0, probe.duration_sec - expected_dur)
            reduction_pct = (
                (silence_removed / probe.duration_sec) * 100.0 if probe.duration_sec > 0 else 0.0
            )
            publish_job_completed(
                self._bus,
                self._notifier,
                job,
                final_output,
                probe.duration_sec,
                expected_dur,
                reduction_pct,
            )
            if self._manifest_repo:
                self._manifest_repo.delete_job(job.job_id)

            return ProcessingResult(
                input_path=job.source_path,
                output_path=final_output,
                original_duration=probe.duration_sec,
                final_duration=expected_dur,
                silence_removed_duration=silence_removed,
                reduction_percentage=reduction_pct,
                segments_retained_count=len(keep_segments),
                manifest_path=manifest_path,
                plot_path=plot_path,
            )

        except JobCancelledException as exc:
            self._handle_terminal_error(job, JobState.CANCELLED, exc.code.value, str(exc))
            self._bus.publish(JobCancelled(job_id=job.job_id, source_path=job.source_path))
            raise
        except AutoSilentTrimmerException as exc:
            self._handle_terminal_error(job, JobState.FAILED, exc.code.value, str(exc))
            raise
        except Exception as exc:
            self._handle_terminal_error(
                job, JobState.FAILED, ErrorCode.INTERNAL_ERROR.value, str(exc)
            )
            raise
        finally:
            if staging_path and os.path.exists(staging_path):
                os.remove(staging_path)
            if temp_work_dir:
                shutil.rmtree(temp_work_dir, ignore_errors=True)

    def _run_probe_stage(self, job: Job) -> MediaProbeInfo:
        self._transition(job, JobState.PROBING)
        probe = self._prober.probe(job.source_path)
        if not probe.is_seekable:
            raise FormatMismatchException(
                f"Media container is not seekable or contains no A/V streams: {job.source_path}"
            )
        job.total_duration = probe.duration_sec
        job.source_size = probe.file_size_bytes
        job.source_mtime = os.path.getmtime(job.source_path)
        return probe

    def _run_plan_stage(
        self,
        job: Job,
        probe: MediaProbeInfo,
        raw_audio: str,
        final_output: str,
        command: ProcessMediaCommand,
    ) -> tuple[list, str | None]:
        self._transition(job, JobState.PLANNING)
        self._check_controls(job)
        if probe.is_video:
            self._media_manager.extract_audio(job.source_path, raw_audio)
        else:
            shutil.copyfile(job.source_path, raw_audio)
        if probe.duration_sec <= 0.0:
            probe = MediaProbeInfo(
                **{**probe.__dict__, "duration_sec": float(sf.info(raw_audio).duration)}
            )
            job.total_duration = probe.duration_sec

        manifest_path = final_output + MANIFEST_SUFFIX
        segments = self._strategy.plan_keep_segments(
            probe_info=probe,
            audio_path=raw_audio,
            manifest_path=manifest_path,
            params=command.strategy_params,
        )
        return segments, manifest_path

    def _merge_and_denoise(
        self,
        *,
        probe: MediaProbeInfo,
        chunk_outputs: list[str],
        merged_raw: str,
        staging_path: str,
        work_dir: str,
    ) -> None:
        self._media_manager.concat_files(chunk_outputs, merged_raw, is_video=probe.is_video)
        if self._noise_reduction is None:
            if probe.is_video:
                shutil.copyfile(merged_raw, staging_path)
            else:
                self._media_manager.export_audio(merged_raw, staging_path)
            return

        cut_raw_audio = os.path.join(work_dir, f"denoise_in{TEMP_AUDIO_SUFFIX}")
        cut_clean_audio = os.path.join(work_dir, f"denoise_out{TEMP_AUDIO_SUFFIX}")
        if probe.is_video:
            self._media_manager.extract_audio(merged_raw, cut_raw_audio)
            audio_in = cut_raw_audio
        else:
            audio_in = merged_raw

        self._noise_reduction.process(audio_in, cut_clean_audio)
        if probe.is_video:
            self._media_manager.merge_audio(merged_raw, cut_clean_audio, staging_path)
        else:
            self._media_manager.export_audio(cut_clean_audio, staging_path)

    def _check_controls(self, job: Job) -> None:
        if self._cancel_requested.is_set():
            raise JobCancelledException("Job cancelled by user request.")
        if not self._pause_event.is_set() and job.state == JobState.RUNNING:
            self._transition(job, JobState.PAUSED)
            self._pause_event.wait()
            if self._cancel_requested.is_set():
                raise JobCancelledException("Job cancelled while paused.")
            self._transition(job, JobState.RUNNING)

    @staticmethod
    def _verify_source_unmodified(job: Job) -> None:
        if not os.path.exists(job.source_path):
            raise SourceLockedException(f"Source vanished during job: {job.source_path}")
        cur_size = os.path.getsize(job.source_path)
        cur_mtime = os.path.getmtime(job.source_path)
        if cur_size != job.source_size or cur_mtime != job.source_mtime:
            raise SourceLockedException(
                f"Source file changed externally during processing: {job.source_path}"
            )

    def _transition(self, job: Job, target: JobState) -> None:
        prev = job.state
        job.transition_to(target)
        self._persist(job)
        publish_stage_transition(self._bus, job, prev, target)

    def _handle_terminal_error(
        self, job: Job, terminal: JobState, error_code: str, msg: str
    ) -> None:
        job.error_code = error_code
        job.error_message = msg
        if not job.is_terminal:
            try:
                job.transition_to(terminal)
            except ValueError:
                job.state = terminal
        self._persist(job)
        if terminal == JobState.FAILED:
            publish_job_failed(self._bus, self._notifier, job, error_code, msg)

    def _persist(self, job: Job) -> None:
        if self._manifest_repo:
            self._manifest_repo.save_job(job)


def _target_temp_ext(probe: MediaProbeInfo) -> str:
    return TEMP_VIDEO_SUFFIX if probe.is_video else TEMP_AUDIO_SUFFIX
