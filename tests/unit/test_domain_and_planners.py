"""Unit tests for domain FSM, planners, output collision resolver, and i18n parity."""

from __future__ import annotations

from pathlib import Path

import pytest
from autosilenttrimmer.application.services.chunk_planner import ChunkPlanner
from autosilenttrimmer.application.services.execution_planner import ExecutionPlanner
from autosilenttrimmer.application.services.output_path_resolver import OutputPathResolver
from autosilenttrimmer.core.config import ExecutionConfig, OutputPolicyConfig
from autosilenttrimmer.core.exceptions import FormatMismatchException
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.core.i18n.catalog_en import MESSAGES_EN
from autosilenttrimmer.core.i18n.catalog_id import MESSAGES_ID
from autosilenttrimmer.domain.entities.job import ChunkStatus, ChunkTask, Job, JobState
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.compute import (
    BackendSelection,
    ComputeCapabilities,
    PlatformSpec,
)
from autosilenttrimmer.domain.models.media_probe import (
    ExecutionMode,
    MediaProbeInfo,
    StreamSummary,
)


def test_job_state_machine_and_weighted_progress() -> None:
    job = Job(source_path="demo.mp4")
    assert job.state == JobState.QUEUED
    assert job.progress_percent == 0.0

    job.transition_to(JobState.PROBING)
    job.transition_to(JobState.PLANNING)
    job.transition_to(JobState.RUNNING)
    job.chunks = [
        ChunkTask(index=0, start_sec=0.0, end_sec=30.0, segments=[], status=ChunkStatus.COMPLETED),
        ChunkTask(index=1, start_sec=30.0, end_sec=90.0, segments=[], status=ChunkStatus.PENDING),
    ]
    # Weighted progress: 30s / 90s = 1/3 through 73% chunk band + 15% base = 39.33%
    assert 38.0 <= job.progress_percent <= 41.0

    with pytest.raises(ValueError):
        job.transition_to(JobState.DONE)  # Cannot jump RUNNING -> DONE skipping MERGING/VERIFYING

    job.transition_to(JobState.MERGING)
    job.transition_to(JobState.VERIFYING)
    job.transition_to(JobState.DONE)
    assert job.is_terminal
    assert job.progress_percent == 100.0


def test_chunk_planner_keyframe_alignment_and_short_bypass() -> None:
    planner = ChunkPlanner(chunk_min_sec=30.0, chunk_max_sec=60.0)
    probe_short = MediaProbeInfo(
        path="short.mp4",
        container_format="mp4",
        extension=".mp4",
        duration_sec=20.0,
        file_size_bytes=1024,
        is_video=True,
    )
    short_chunks = planner.plan_chunks(
        probe_short, [MediaSegment(start=1.0, end=12.0)], ExecutionMode.REENCODE, worker_count=4
    )
    assert len(short_chunks) == 1

    # Single huge segment split near keyframes [28.0, 62.0]
    probe_long = MediaProbeInfo(
        path="long.mp4",
        container_format="mp4",
        extension=".mp4",
        duration_sec=150.0,
        file_size_bytes=10_000_000,
        is_video=True,
        video_streams=(StreamSummary(index=0, media_type="video", codec_name="h264"),),
        keyframe_timestamps=(0.0, 28.5, 59.0, 91.5, 120.0),
    )
    chunks = planner.plan_chunks(
        probe_long,
        [MediaSegment(start=0.0, end=140.0)],
        ExecutionMode.REENCODE,
        worker_count=2,
    )
    assert len(chunks) >= 2
    assert any(seg.end in {28.5, 59.0, 91.5} for ch in chunks for seg in ch.keep_segments)


def test_execution_planner_adaptive_worker_cap() -> None:
    caps = ComputeCapabilities(
        platform_spec=PlatformSpec(os_name="windows", arch="x86_64"),
        logical_cores=16,
        physical_cores=8,
        total_ram_bytes=16 * 1024**3,
        available_ram_bytes=1024 * 1024 * 1024,  # 1024 MB -> max 2 workers at 512MB/worker
        ai_device="cpu",
        hw_video_encoders=("h264_nvenc",),
    )
    backend = BackendSelection(
        backend_id="gpu-nvenc",
        ai_device="cpu",
        video_encoder="h264_nvenc",
        max_concurrency=4,
        is_gpu=True,
        reason="ok",
    )
    workers = ExecutionPlanner.calculate_adaptive_workers(caps, backend, ExecutionMode.REENCODE)
    assert workers == 2

    cfg = ExecutionConfig()
    probe = MediaProbeInfo(
        path="a.mp4",
        container_format="mp4",
        extension=".mp4",
        duration_sec=120.0,
        file_size_bytes=2_000_000,
        is_video=True,
    )
    plan = ExecutionPlanner().build_plan(
        probe, [MediaSegment(0.0, 100.0)], caps, backend, cfg, requires_frame_accuracy=False
    )
    assert plan.mode == ExecutionMode.COPY
    assert plan.video_encoder == "copy"

    multi_plan = ExecutionPlanner().build_plan(
        probe,
        [MediaSegment(1.0, 4.0), MediaSegment(8.0, 12.0)],
        caps,
        backend,
        ExecutionConfig(frame_accurate=False),
        requires_frame_accuracy=True,
    )
    assert multi_plan.mode == ExecutionMode.REENCODE
    assert multi_plan.video_encoder == "h264_nvenc"


def test_output_path_resolver_non_destructive_and_increments(tmp_path: Path) -> None:
    src = tmp_path / "interview.mp4"
    src.write_bytes(b"source")

    # Never overwrite source explicitly
    with pytest.raises(FormatMismatchException):
        OutputPathResolver.resolve(str(src), explicit_output_path=str(src))

    first = OutputPathResolver.resolve(str(src), policy=OutputPolicyConfig())
    assert first.endswith("interview.trimmed.mp4")

    Path(first).write_bytes(b"existing")
    second = OutputPathResolver.resolve(str(src), policy=OutputPolicyConfig())
    assert second.endswith("interview.trimmed_1.mp4")


def test_bilingual_i18n_catalog_parity() -> None:
    assert set(MESSAGES_EN.keys()) == set(MESSAGES_ID.keys())
    l10n = Localizer("id")
    assert "Pemotongan" in l10n.text("notify.completed_title")
    assert l10n.toggle_language() == "en"
    assert "Trim Complete" in l10n.text("notify.completed_title")


def test_auto_silence_strategy_clamps_segments_to_media_duration() -> None:
    from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
    from autosilenttrimmer.infrastructure.strategies.auto_silence import AutoSilenceTrimStrategy

    class _OvershootVAD(IVoiceActivityDetector):
        def get_keep_segments(
            self, audio_path: str, manifest_path: str | None = None
        ) -> list[MediaSegment]:
            return [
                MediaSegment(start=1.0, end=9.5),
                MediaSegment(start=10.5, end=12.0),
            ]

    probe = MediaProbeInfo(
        path="demo.mp4",
        container_format="mp4",
        extension=".mp4",
        duration_sec=8.25,
        file_size_bytes=1024,
        is_video=True,
    )
    segs = AutoSilenceTrimStrategy(_OvershootVAD()).plan_keep_segments(probe)
    assert segs == [MediaSegment(start=1.0, end=8.25)]


def test_silero_vad_rejects_unsupported_sample_rate() -> None:
    from autosilenttrimmer.core.config import VADConfig
    from autosilenttrimmer.infrastructure.vad.silero import SileroBasedVAD

    vad = SileroBasedVAD(VADConfig(sample_rate_vad=48000))
    with pytest.raises(ValueError, match="Silero VAD supports only sample rates"):
        vad.get_keep_segments("unused.wav")
