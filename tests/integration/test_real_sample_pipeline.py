"""Industrial end-to-end integration tests using the 1-minute real 1080p speech sample."""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path

import pytest
from autosilenttrimmer.application.use_cases.job_orchestrator import JobOrchestrator
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.models.events import JobCompleted, JobFailed
from autosilenttrimmer.domain.models.processing_command import ProcessMediaCommand
from autosilenttrimmer.domain.models.settings import UserSettings
from autosilenttrimmer.infrastructure.compute.backend_selector import PolicyComputeBackend
from autosilenttrimmer.infrastructure.compute.capability_prober import (
    CrossPlatformCapabilityProber,
)
from autosilenttrimmer.infrastructure.events.in_memory_bus import InMemoryEventBus
from autosilenttrimmer.infrastructure.ipc.gateway import LocalIPCClient, LocalIPCGateway
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.pyav_prober import PyAVMediaProber
from autosilenttrimmer.infrastructure.media.pyav_verifier import PyAVMediaVerifier
from autosilenttrimmer.infrastructure.runtime.pack_manager import compute_sha256
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.presentation.cli.runtime_builder import build_runtime_components

REAL_SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "real_sample_1m.mp4"

requires_real_sample = pytest.mark.skipif(
    not REAL_SAMPLE.is_file(),
    reason="Real 1-minute sample video not present at samples/real_sample_1m.mp4",
)


@requires_real_sample
def test_real_sample_baseline_vs_tuned_settings_measurable_impact(tmp_path: Path) -> None:
    """Verify baseline Silero vs aggressive Energy vs CPU CRF28 change duration, size, & verify."""
    src_sha = compute_sha256(str(REAL_SAMPLE))
    prober = PyAVMediaProber()
    src_probe = prober.probe(str(REAL_SAMPLE))
    locator = ManagedFFmpegLocator()
    cap_prober = CrossPlatformCapabilityProber(locator)

    def _run_with(settings: UserSettings, out_name: str):
        comps = build_runtime_components(
            settings=settings, locator=locator, localizer=Localizer("en")
        )
        orch = JobOrchestrator(
            media_manager=comps.media_manager,
            media_prober=prober,
            media_verifier=comps.media_verifier,
            trim_strategy=comps.trim_strategy,
            capability_prober=cap_prober,
            compute_backend=PolicyComputeBackend(cap_prober),
            event_bus=InMemoryEventBus(),
            config=comps.config,
            noise_reduction=comps.noise_reduction,
            visualizer=comps.visualizer,
        )
        out_path = str(tmp_path / out_name)
        cmd = ProcessMediaCommand(
            input_path=str(REAL_SAMPLE),
            output_path=out_path,
            strategy=settings.trim_strategy,
            vad_method=settings.vad_engine,
            noise_reduction_method=settings.noise_reduction_method,
            min_silence_gap=settings.min_silence_gap,
            pad=settings.pad,
            compute_policy=settings.compute_policy,
            max_workers=settings.max_workers,
            on_conflict="overwrite",
        )
        res = orch.execute_job(cmd)
        vrep = PyAVMediaVerifier(
            duration_tolerance_sec=settings.verify_duration_tolerance_sec
        ).verify(
            res.output_path,
            expected_duration_sec=res.final_duration,
            expected_has_video=True,
            expected_audio_streams=1,
        )
        assert vrep.passed, f"{out_name}: {vrep.failure_reason}"
        return res, prober.probe(res.output_path)

    # 1. Default Silero G2
    s_default = UserSettings(enable_notifications=False)
    res_base, probe_base = _run_with(s_default, "out_base.mp4")

    # 2. Tight Energy VAD -> must cut meaningfully without corruption
    s_energy = UserSettings(
        vad_engine="energy",
        min_silence_gap=0.15,
        pad=0.05,
        energy_db_offset=18.0,
        enable_notifications=False,
    )
    res_energy, probe_energy = _run_with(s_energy, "out_energy.mp4")

    # 3. CPU libx264 CRF 28 multi-chunk + Spectral Denoise
    s_crf = UserSettings(
        vad_engine="energy",
        noise_reduction_method="spectral",
        compute_policy="g3_cpu_only",
        x264_preset="veryfast",
        x264_crf=28,
        max_workers=2,
        min_chunkable_duration_sec=15.0,
        target_chunk_min_sec=10.0,
        target_chunk_max_sec=20.0,
        enable_notifications=False,
    )
    res_crf, probe_crf = _run_with(s_crf, "out_cpu_crf28.mp4")

    assert compute_sha256(str(REAL_SAMPLE)) == src_sha
    assert probe_base.duration_sec < src_probe.duration_sec
    assert res_base.reduction_percentage > 5.0
    assert probe_energy.duration_sec < src_probe.duration_sec
    assert res_energy.reduction_percentage > 5.0
    assert probe_crf.duration_sec < src_probe.duration_sec
    assert res_crf.segments_retained_count >= 1
    assert probe_crf.file_size_bytes < src_probe.file_size_bytes
    assert probe_crf.video_streams[0].codec_name == "h264"


@requires_real_sample
def test_real_sample_tune_save_ipc_hot_reload_end_to_end(tmp_path: Path) -> None:
    """Verify TuneWindow Apply & Save -> IPC reload_settings -> daemon trims real sample."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from autosilenttrimmer.presentation.tune.tune_window import TuneWindow
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert app is not None

    settings_file = str(tmp_path / "settings.json")
    custom_out_dir = tmp_path / "custom_tuned_out"
    custom_out_dir.mkdir()
    repo = JsonSettingsRepository(settings_file)
    repo.save(UserSettings(enable_notifications=False))

    addr = (
        rf"\\.\pipe\test_real_daemon_{uuid.uuid4().hex[:8]}"
        if os.name == "nt"
        else str(tmp_path / "gw.sock")
    )
    fam = "AF_PIPE" if os.name == "nt" else "AF_UNIX"

    locator = ManagedFFmpegLocator()
    cap_prober = CrossPlatformCapabilityProber(locator)
    localizer = Localizer("en")
    bus = InMemoryEventBus()
    comps = build_runtime_components(settings=repo.load(), locator=locator, localizer=localizer)
    orch = JobOrchestrator(
        media_manager=comps.media_manager,
        media_prober=PyAVMediaProber(),
        media_verifier=comps.media_verifier,
        trim_strategy=comps.trim_strategy,
        capability_prober=cap_prober,
        compute_backend=PolicyComputeBackend(cap_prober),
        event_bus=bus,
        config=comps.config,
    )
    done_ev = threading.Event()
    outputs: list[str] = []
    errors: list[str] = []
    bus.subscribe(JobCompleted, lambda ev: (outputs.append(ev.output_path), done_ev.set()))  # type: ignore[arg-type]
    bus.subscribe(JobFailed, lambda ev: (errors.append(ev.message), done_ev.set()))  # type: ignore[arg-type]
    orch.start_background_worker()

    def _reload() -> UserSettings:
        fresh = repo.load()
        localizer.set_language(fresh.language)
        fc = build_runtime_components(settings=fresh, locator=locator, localizer=localizer)
        orch.reconfigure(
            config=fc.config,
            media_manager=fc.media_manager,
            media_verifier=fc.media_verifier,
            trim_strategy=fc.trim_strategy,
            noise_reduction=fc.noise_reduction,
            visualizer=fc.visualizer,
        )
        return fresh

    def _on_batch(paths: list[str]) -> None:
        cur = _reload()
        orch.enqueue(
            [
                ProcessMediaCommand(
                    input_path=p,
                    strategy=cur.trim_strategy,
                    vad_method=cur.vad_engine,
                    noise_reduction_method=cur.noise_reduction_method,
                    min_silence_gap=cur.min_silence_gap,
                    pad=cur.pad,
                    ffmpeg_path=cur.ffmpeg_path,
                    compute_policy=cur.compute_policy,
                    max_workers=cur.max_workers,
                    on_conflict=cur.on_conflict,
                    output_location=cur.output_location,
                    output_naming_template=cur.output_naming_template,
                )
                for p in paths
            ]
        )

    gw = LocalIPCGateway(address=addr, family=fam, coalesce_window_sec=0.1)
    gw.start(_on_batch, on_reload_settings=_reload)
    client = LocalIPCClient(address=addr, family=fam)

    win = TuneWindow(
        settings_repo=repo,
        settings_file_path=settings_file,
        gateway_client=client,
    )
    try:
        win._controls["vad_engine"].setter("energy")
        win._controls["compute_policy"].setter("g3_cpu_only")
        win._controls["x264_crf"].setter(28)
        win._controls["output_location"].setter("custom")
        win._controls["output_custom_dir"].setter(str(custom_out_dir))
        win._controls["output_naming_template"].setter("{name}_qt_hot.{ext}")
        win._controls["enable_notifications"].setter(False)
        win._apply_btn.click()

        assert client.enqueue_paths([str(REAL_SAMPLE)])
        assert done_ev.wait(timeout=180.0), "Hot-reloaded real sample job timed out"
        assert not errors, f"Job failed: {errors}"
        assert len(outputs) == 1
        out_file = Path(outputs[0])
        assert out_file.parent == custom_out_dir
        assert out_file.name == "real_sample_1m_qt_hot.mp4"
        assert out_file.is_file()
        assert PyAVMediaProber().probe(str(out_file)).duration_sec < 66.7
    finally:
        win.close()
        orch.stop_background_worker()
        gw.stop()
