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

    custom_dir = tmp_path / "project_exports"
    overridden = OutputPathResolver.resolve(
        str(src),
        policy=OutputPolicyConfig(),
        output_dir=str(custom_dir),
    )
    assert Path(overridden).parent == custom_dir
    assert Path(overridden).name == "interview.trimmed.mp4"


def test_resolve_with_disk_guard_prompts_and_relocates_off_full_volume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disk guard checks target volume and relocates via prompt callback when full."""
    import os
    import shutil
    from collections import namedtuple

    from autosilenttrimmer.core.exceptions import DiskFullException, JobCancelledException
    from autosilenttrimmer.domain.models.processing_command import (
        DestinationPromptRequest,
        ProcessMediaCommand,
    )

    Usage = namedtuple("Usage", ["total", "used", "free"])
    full_dir = tmp_path / "full_drive"
    spacious_dir = tmp_path / "spacious_drive"
    full_dir.mkdir()
    spacious_dir.mkdir()
    src = full_dir / "big.mp4"
    src.write_bytes(b"video")

    def _fake_disk_usage(path: str) -> Usage:
        norm = os.path.normcase(os.path.abspath(path))
        if norm.startswith(os.path.normcase(str(spacious_dir))):
            return Usage(total=10 * 1024**3, used=1 * 1024**3, free=9 * 1024**3)
        return Usage(total=10 * 1024**3, used=10 * 1024**3, free=5 * 1024**2)

    monkeypatch.setattr(shutil, "disk_usage", _fake_disk_usage)

    probe = MediaProbeInfo(
        path=str(src),
        container_format="mp4",
        extension=".mp4",
        duration_sec=10.0,
        file_size_bytes=500 * 1024**2,
        is_video=True,
    )
    cmd = ProcessMediaCommand(input_path=str(src))

    with pytest.raises(DiskFullException):
        OutputPathResolver.resolve_with_disk_guard(
            probe=probe, command=cmd, policy=OutputPolicyConfig(), on_destination_needed=None
        )

    prompts: list[DestinationPromptRequest] = []

    def _pick_spacious(req: DestinationPromptRequest) -> str:
        prompts.append(req)
        return str(spacious_dir)

    relocated = OutputPathResolver.resolve_with_disk_guard(
        probe=probe, command=cmd, policy=OutputPolicyConfig(), on_destination_needed=_pick_spacious
    )
    assert Path(relocated).parent == spacious_dir
    assert Path(relocated).name == "big.trimmed.mp4"
    assert len(prompts) == 1
    assert Path(prompts[0].target_path).parent == full_dir

    with pytest.raises(JobCancelledException):
        OutputPathResolver.resolve_with_disk_guard(
            probe=probe,
            command=cmd,
            policy=OutputPolicyConfig(),
            on_destination_needed=lambda _req: None,
        )


def test_job_orchestrator_places_work_dir_on_relocated_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JobOrchestrator creates temp_work_dir on chosen destination drive after low-disk redirect."""
    import os
    import shutil
    import tempfile
    from collections import namedtuple

    from autosilenttrimmer.application.use_cases.job_orchestrator import JobOrchestrator
    from autosilenttrimmer.core.config import MediaProcessingConfig
    from autosilenttrimmer.domain.contracts.compute import ICapabilityProber, IComputeBackend
    from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
    from autosilenttrimmer.domain.contracts.media_prober import IMediaProber
    from autosilenttrimmer.domain.contracts.media_verifier import (
        IMediaVerifier,
        VerificationReport,
    )
    from autosilenttrimmer.domain.contracts.trim_strategy import ITrimStrategy
    from autosilenttrimmer.domain.models.compute import ComputePolicy
    from autosilenttrimmer.domain.models.processing_command import ProcessMediaCommand
    from autosilenttrimmer.infrastructure.events.in_memory_bus import InMemoryEventBus

    Usage = namedtuple("Usage", ["total", "used", "free"])
    src_dir = tmp_path / "full_c"
    alt_dir = tmp_path / "spacious_d"
    src_dir.mkdir()
    alt_dir.mkdir()
    src = src_dir / "clip.mp4"
    src.write_bytes(b"source-bytes")

    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda p: (
            Usage(total=10 * 1024**3, used=1 * 1024**3, free=9 * 1024**3)
            if os.path.normcase(os.path.abspath(p)).startswith(os.path.normcase(str(alt_dir)))
            else Usage(total=10 * 1024**3, used=10 * 1024**3, free=1024)
        ),
    )

    mkdtemp_dirs: list[str] = []
    real_mkdtemp = tempfile.mkdtemp

    def _spy_mkdtemp(*args, **kwargs) -> str:
        if kwargs.get("dir"):
            mkdtemp_dirs.append(str(kwargs["dir"]))
        return real_mkdtemp(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkdtemp", _spy_mkdtemp)

    class _Prober(IMediaProber):
        def probe(self, path: str) -> MediaProbeInfo:
            return MediaProbeInfo(
                path=path,
                container_format="mp4",
                extension=".mp4",
                duration_sec=5.0,
                file_size_bytes=src.stat().st_size,
                is_video=True,
                video_streams=(StreamSummary(index=0, media_type="video", codec_name="h264"),),
                audio_streams=(StreamSummary(index=1, media_type="audio", codec_name="aac"),),
            )

    class _Mgr(IMediaManager):
        def extract_audio(self, source_media_path: str, destination_audio_path: str) -> None:
            Path(destination_audio_path).write_bytes(b"wav")

        def slice_and_concat(
            self,
            media_path: str,
            segments: list[MediaSegment],
            output_path: str,
            *,
            video_encoder: str = "libx264",
            copy_mode: bool = False,
        ) -> None:
            Path(output_path).write_bytes(b"chunk")

        def concat_files(self, chunk_paths: list[str], output_path: str, is_video: bool) -> None:
            Path(output_path).write_bytes(b"merged")

        def merge_audio(self, video_path: str, clean_audio_path: str, output_path: str) -> None:
            Path(output_path).write_bytes(b"staged")

        def export_audio(self, clean_audio_path: str, output_path: str) -> None:
            Path(output_path).write_bytes(b"audio")

    class _Strategy(ITrimStrategy):
        @property
        def strategy_id(self) -> str:
            return "stub"

        @property
        def requires_frame_accuracy(self) -> bool:
            return False

        def plan_keep_segments(self, probe_info, audio_path=None, manifest_path=None, params=None):
            return [MediaSegment(start=0.0, end=3.0)]

    class _Caps(ICapabilityProber):
        def probe(self) -> ComputeCapabilities:
            return ComputeCapabilities(
                platform_spec=PlatformSpec(os_name="windows", arch="x86_64"),
                logical_cores=4,
                physical_cores=4,
                total_ram_bytes=8 * 1024**3,
                available_ram_bytes=4 * 1024**3,
                ai_device="cpu",
                hw_video_encoders=(),
            )

    class _Backend(IComputeBackend):
        def select_backend(self, policy, ffmpeg_path, requested_max_workers=None):
            return BackendSelection(
                backend_id="cpu",
                ai_device="cpu",
                video_encoder="libx264",
                max_concurrency=1,
                is_gpu=False,
                reason="ok",
            )

        def fallback_to_cpu(self, reason: str):
            return self.select_backend(ComputePolicy.CPU_ONLY, "")

    class _Verifier(IMediaVerifier):
        def verify(self, *args, **kwargs) -> VerificationReport:
            return VerificationReport(
                passed=True,
                actual_duration_sec=3.0,
                expected_duration_sec=3.0,
                streams_matched=True,
                decode_samples_checked=2,
            )

    orch = JobOrchestrator(
        media_manager=_Mgr(),
        media_prober=_Prober(),
        media_verifier=_Verifier(),
        trim_strategy=_Strategy(),
        capability_prober=_Caps(),
        compute_backend=_Backend(),
        event_bus=InMemoryEventBus(),
        config=MediaProcessingConfig(),
        on_destination_needed=lambda _req: str(alt_dir),
    )

    result = orch.execute_job(ProcessMediaCommand(input_path=str(src)))
    assert Path(result.output_path).parent == alt_dir
    assert Path(result.output_path).is_file()
    assert mkdtemp_dirs == [str(alt_dir)]


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


def test_pyav_prober_extracts_indexed_keyframes_fast(golden_mp4: str) -> None:
    from autosilenttrimmer.infrastructure.media.pyav_prober import PyAVMediaProber

    info = PyAVMediaProber().probe(golden_mp4)
    assert info.is_video
    assert info.is_seekable
    assert len(info.keyframe_timestamps) >= 2
    assert info.keyframe_timestamps[0] == pytest.approx(0.0, abs=0.1)
