"""Run 9-case sparse configuration verification matrix on real 1-minute sample video."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.presentation.cli.runtime_builder import build_runtime_components


@dataclasses.dataclass(frozen=True)
class MatrixCase:
    """One sparse setting permutation executed against the real sample video."""

    case_id: str
    overrides: dict[str, Any]
    strategy_params: dict[str, Any] | None = None
    via_daemon_ipc: bool = False


def build_sparse_cases(custom_out_dir: str, whisper_lang: str) -> list[MatrixCase]:
    """Build 9 orthogonal cases covering all 5 Tune configuration tabs."""
    return [
        MatrixCase("01_baseline_silero_g2", {}),
        MatrixCase(
            "02_energy_aggressive",
            {
                "vad_engine": "energy",
                "min_silence_gap": 0.15,
                "pad": 0.05,
                "energy_db_offset": 18.0,
                "energy_min_len_sec": 0.20,
            },
        ),
        MatrixCase(
            "03_silero_padded_8k",
            {
                "vad_engine": "silero",
                "min_silence_gap": 1.20,
                "pad": 0.45,
                "silero_min_speech_duration_ms": 400,
                "sample_rate_vad": 8000,
            },
        ),
        MatrixCase(
            "04_whisper_semantic",
            {
                "vad_engine": "whisper",
                "whisper_model_size": "tiny",
                "whisper_language": whisper_lang,
                "whisper_no_speech_threshold": 0.50,
                "whisper_max_word_duration_sec": 8.0,
            },
        ),
        MatrixCase(
            "05_spectral_denoise_viz",
            {
                "vad_engine": "energy",
                "noise_reduction_method": "spectral",
                "spectral_prop_decrease": 0.85,
                "audio_bitrate": "128k",
                "generate_visual_artifacts": True,
            },
        ),
        MatrixCase(
            "06_deepfilter_neural",
            {
                "vad_engine": "silero",
                "noise_reduction_method": "deepfilter",
                "deepfilter_chunk_duration_sec": 10,
                "sample_rate_deepfilter": 48000,
            },
        ),
        MatrixCase(
            "07_cpu_x264_chunked",
            {
                "compute_policy": "g3_cpu_only",
                "x264_preset": "veryfast",
                "x264_crf": 28,
                "max_workers": 2,
                "min_chunkable_duration_sec": 15.0,
                "target_chunk_min_sec": 10.0,
                "target_chunk_max_sec": 20.0,
                "audio_bitrate": "128k",
            },
        ),
        MatrixCase(
            "08_daemon_hotreload_manual_copy",
            {
                "trim_strategy": "manual-range",
                "frame_accurate": False,
                "output_location": "custom",
                "output_custom_dir": custom_out_dir,
                "output_naming_template": "{name}_tuned.{ext}",
                "on_conflict": "increment",
                "enable_notifications": False,
                "language": "id",
            },
            strategy_params={"start_sec": 8.366667, "end_sec": 50.033333},
            via_daemon_ipc=True,
        ),
        MatrixCase(
            "09_copy_multi_segment_energy",
            {
                "vad_engine": "energy",
                "frame_accurate": False,
                "min_silence_gap": 0.5,
            },
        ),
    ]


def _run_daemon_ipc_case(
    case: MatrixCase,
    sample_path: str,
    out_dir: Path,
    locator: ManagedFFmpegLocator,
    cap_prober: CrossPlatformCapabilityProber,
) -> tuple[str, int, str | None]:
    """Exercise Tune repository save -> IPC reload_settings -> daemon queue execution."""
    settings_path = str(out_dir / "case08_settings.json")
    repo = JsonSettingsRepository(settings_path)
    repo.save(UserSettings())  # Start with baseline defaults

    localizer = Localizer("en")
    bus = InMemoryEventBus()
    base_comps = build_runtime_components(
        settings=repo.load(), locator=locator, localizer=localizer
    )
    orch = JobOrchestrator(
        media_manager=base_comps.media_manager,
        media_prober=PyAVMediaProber(),
        media_verifier=base_comps.media_verifier,
        trim_strategy=base_comps.trim_strategy,
        capability_prober=cap_prober,
        compute_backend=PolicyComputeBackend(cap_prober),
        event_bus=bus,
        config=base_comps.config,
        noise_reduction=base_comps.noise_reduction,
        visualizer=base_comps.visualizer,
        priority_ctrl=base_comps.priority_ctrl,
    )
    done_ev = threading.Event()
    completed_path: list[str] = []
    failed_msg: list[str] = []

    def _on_done(ev: JobCompleted) -> None:
        completed_path.append(ev.output_path)
        done_ev.set()

    def _on_fail(ev: JobFailed) -> None:
        failed_msg.append(f"{ev.error_code}: {ev.message}")
        done_ev.set()

    bus.subscribe(JobCompleted, _on_done)  # type: ignore[arg-type]
    bus.subscribe(JobFailed, _on_fail)  # type: ignore[arg-type]
    orch.start_background_worker()

    sock_addr = str(out_dir / "matrix_gw.sock") if os.name != "nt" else r"\\.\pipe\trim_matrix_gw"
    fam = "AF_UNIX" if os.name != "nt" else "AF_PIPE"
    gw = LocalIPCGateway(address=sock_addr, family=fam, coalesce_window_sec=0.1)

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
            priority_ctrl=fc.priority_ctrl,
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
                    strategy_params=case.strategy_params,
                )
                for p in paths
            ]
        )

    gw.start(_on_batch, on_reload_settings=_reload)
    try:
        # Persist tuned settings (simulating TuneWindow Apply & Save) and hot-reload daemon
        repo.save(UserSettings.from_dict(case.overrides))
        client = LocalIPCClient(address=sock_addr, family=fam)
        assert client.notify_settings_updated()
        assert client.enqueue_paths([sample_path])
        assert done_ev.wait(timeout=180.0), "Daemon job timed out"
        if failed_msg:
            raise RuntimeError(failed_msg[0])
        out_path = completed_path[0]
        return out_path, 1, None
    finally:
        orch.stop_background_worker()
        gw.stop()


def run_matrix(sample_path: str, out_dir: Path, whisper_lang: str) -> list[dict[str, Any]]:
    """Execute all sparse matrix cases and emit empirical container metrics."""
    out_dir.mkdir(parents=True, exist_ok=True)
    custom_dir = out_dir / "case08_custom"
    custom_dir.mkdir(parents=True, exist_ok=True)

    prober = PyAVMediaProber()
    src_info = prober.probe(sample_path)
    locator = ManagedFFmpegLocator()
    cap_prober = CrossPlatformCapabilityProber(locator)
    cases = build_sparse_cases(str(custom_dir), whisper_lang=whisper_lang)
    results: list[dict[str, Any]] = []

    print(
        f"Source sample: {sample_path} | duration={src_info.duration_sec:.2f}s "
        f"| size={src_info.file_size_bytes / 1048576:.2f} MB "
        f"| {src_info.video_streams[0].width}x{src_info.video_streams[0].height} "
        f"| video={src_info.video_streams[0].codec_name} audio={src_info.audio_streams[0].codec_name}"
    )

    for case in cases:
        t0 = time.monotonic()
        row: dict[str, Any] = {"case_id": case.case_id, "overrides": case.overrides}
        try:
            if case.via_daemon_ipc:
                out_path, segs, manifest_p = _run_daemon_ipc_case(
                    case, sample_path, out_dir, locator, cap_prober
                )
                expected_dur = 50.033333 - 8.366667
                tol = UserSettings().verify_duration_tolerance_sec
                plot_p = None
            else:
                tuned = UserSettings.from_dict({**case.overrides, "enable_notifications": False})
                comps = build_runtime_components(
                    settings=tuned, locator=locator, localizer=Localizer(tuned.language)
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
                    priority_ctrl=comps.priority_ctrl,
                )
                target_mp4 = str(out_dir / f"{case.case_id}.mp4")
                cmd = ProcessMediaCommand(
                    input_path=sample_path,
                    output_path=target_mp4,
                    strategy=tuned.trim_strategy,
                    vad_method=tuned.vad_engine,
                    noise_reduction_method=tuned.noise_reduction_method,
                    min_silence_gap=tuned.min_silence_gap,
                    pad=tuned.pad,
                    ffmpeg_path=comps.ffmpeg_path,
                    compute_policy=tuned.compute_policy,
                    max_workers=tuned.max_workers,
                    on_conflict="overwrite",
                    output_location=tuned.output_location,
                    output_naming_template=tuned.output_naming_template,
                    strategy_params=case.strategy_params,
                )
                res = orch.execute_job(cmd)
                out_path = res.output_path
                segs = res.segments_retained_count
                manifest_p = res.manifest_path
                plot_p = res.plot_path
                expected_dur = res.final_duration
                tol = tuned.verify_duration_tolerance_sec

            out_info = prober.probe(out_path)
            vrep = PyAVMediaVerifier(duration_tolerance_sec=tol).verify(
                out_path,
                expected_duration_sec=expected_dur,
                expected_has_video=True,
                expected_audio_streams=1,
            )
            delta = src_info.duration_sec - out_info.duration_sec
            pct = (delta / src_info.duration_sec) * 100.0 if src_info.duration_sec > 0 else 0.0
            row.update(
                {
                    "status": "OK" if vrep.passed else "VERIFY_FAIL",
                    "output_path": out_path,
                    "input_duration_sec": round(src_info.duration_sec, 3),
                    "output_duration_sec": round(out_info.duration_sec, 3),
                    "duration_reduced_sec": round(delta, 3),
                    "reduction_pct": round(pct, 2),
                    "output_size_mb": round(out_info.file_size_bytes / 1048576, 2),
                    "video_codec": out_info.video_streams[0].codec_name
                    if out_info.video_streams
                    else None,
                    "audio_bitrate_kbps": round((out_info.audio_streams[0].bit_rate or 0) / 1000, 1)
                    if out_info.audio_streams
                    else None,
                    "segments_retained": segs,
                    "manifest_exists": bool(manifest_p and os.path.isfile(manifest_p)),
                    "plot_exists": bool(plot_p and os.path.isfile(plot_p)),
                    "verify_passed": vrep.passed,
                    "verify_samples": vrep.decode_samples_checked,
                    "verify_note": vrep.failure_reason,
                    "elapsed_sec": round(time.monotonic() - t0, 2),
                    "error": None,
                }
            )
        except Exception as exc:
            row.update(
                {
                    "status": "ERROR",
                    "elapsed_sec": round(time.monotonic() - t0, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        results.append(row)
        print(
            f"  [{row['status']}] {case.case_id}: dur={row.get('output_duration_sec', '-')}"
            f"s (cut={row.get('reduction_pct', '-')}%) size={row.get('output_size_mb', '-')}MB "
            f"segs={row.get('segments_retained', '-')} elapsed={row['elapsed_sec']}s"
            f"{' ERR=' + str(row['error']) if row.get('error') else ''}"
        )

    report_path = out_dir / "sparse_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved sparse JSON report: {report_path}")
    return results


def main() -> int:
    """CLI entrypoint for running the sparse real-video configuration verification suite."""
    parser = argparse.ArgumentParser(description="Run 9-case sparse test on real sample video.")
    parser.add_argument(
        "--input",
        default=os.path.join(PROJECT_ROOT, "samples", "real_sample_1m.mp4"),
        help="Path to the ~1 minute sample video",
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.join(PROJECT_ROOT, "samples", "results"),
        help="Directory for trimmed outputs and sparse_report.json",
    )
    parser.add_argument(
        "--whisper-lang",
        default="id",
        help="Language code passed to Whisper VAD in case 04",
    )
    args = parser.parse_args()
    if not os.path.isfile(args.input):
        print(f"Sample input video not found: {args.input}", file=sys.stderr)
        return 1
    results = run_matrix(args.input, Path(args.out_dir), whisper_lang=args.whisper_lang)
    failures = [r for r in results if r["status"] != "OK"]
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
