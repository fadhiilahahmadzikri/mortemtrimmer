"""Unit tests for unified UserSettings schema, config mapping, FFmpeg wiring, and PyQt6 Tune UI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from autosilenttrimmer.core.settings_schema import SETTINGS_BY_KEY, TUNE_TABS
from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration
from autosilenttrimmer.domain.models.settings import UserSettings
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.ffmpeg_manager import FFmpegMediaManager
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.presentation.cli.parser import build_argument_parser
from autosilenttrimmer.presentation.cli.runtime_builder import merge_cli_overrides


class _FakeGatewayClient(IJobGatewayClient):
    def __init__(self) -> None:
        self.reload_calls = 0

    def is_daemon_running(self) -> bool:
        return True

    def enqueue_paths(self, paths: list[str]) -> bool:
        return True

    def notify_settings_updated(self) -> bool:
        self.reload_calls += 1
        return True


class _FakeShell(IShellIntegration):
    def __init__(self) -> None:
        self.registered = False

    def register(self, executable_path: str, label: str, extensions: frozenset[str]) -> None:
        self.registered = True

    def unregister(self, extensions: frozenset[str]) -> None:
        self.registered = False

    def is_registered(self, extensions: frozenset[str]) -> bool:
        return self.registered


def test_user_settings_and_schema_complete_parity() -> None:
    """Every persisted UserSettings field must map 1-to-1 with SETTINGS_BY_KEY."""
    model_fields = set(UserSettings.__dataclass_fields__.keys())
    schema_fields = set(SETTINGS_BY_KEY.keys())
    assert model_fields == schema_fields


def test_user_settings_sanitization_and_processing_config_mapping() -> None:
    raw = {
        "vad_engine": "nonexistent_engine",
        "x264_crf": 99,
        "sample_rate_vad": 48000,
        "max_workers": 0,
        "x264_preset": "medium",
        "audio_bitrate": "192k",
        "min_silence_gap": 0.35,
        "verify_duration_tolerance_sec": 1.25,
        "disk_space_safety_factor": 3.2,
        "unknown_extra_field": "ignored",
    }
    sanitized = UserSettings.from_dict(raw)
    assert sanitized.vad_engine == "silero"
    assert sanitized.x264_crf == 51
    assert sanitized.sample_rate_vad == 16000
    assert sanitized.max_workers is None
    assert sanitized.x264_preset == "medium"

    cfg = sanitized.to_processing_config()
    assert cfg.audio.x264_preset == "medium"
    assert cfg.audio.x264_crf == "51"
    assert cfg.audio.bitrate == "192k"
    assert cfg.vad.min_silence_gap == pytest.approx(0.35)
    assert cfg.execution.verify_duration_tolerance_sec == pytest.approx(1.25)
    assert cfg.output_policy.disk_space_safety_factor == pytest.approx(3.2)


def test_ffmpeg_manager_consumes_tuned_audio_and_codec_config() -> None:
    ffmpeg_path = ManagedFFmpegLocator().locate()
    tuned = UserSettings(x264_preset="medium", x264_crf=22, audio_bitrate="192k")
    cfg = tuned.to_processing_config()
    mgr = FFmpegMediaManager(ffmpeg_path, audio_config=cfg.audio)
    args = mgr._video_codec_args("libx264")
    assert "-crf" in args and args[args.index("-crf") + 1] == "22"
    assert "-preset" in args and args[args.index("-preset") + 1] == "medium"
    assert "-b:a" in args and args[args.index("-b:a") + 1] == "192k"


def test_cli_merge_inherits_saved_settings_and_respects_explicit_flags() -> None:
    saved = UserSettings(
        vad_engine="energy", min_silence_gap=0.35, noise_reduction_method="spectral"
    )
    parser = build_argument_parser()

    # No tuning flags passed -> inherits saved settings.json
    parsed_default = parser.parse_args(["-i", "demo.mp4"])
    effective = merge_cli_overrides(saved, parsed_default)
    assert effective.vad_engine == "energy"
    assert effective.min_silence_gap == pytest.approx(0.35)
    assert effective.noise_reduction_method == "spectral"

    # Explicit flags override saved settings cleanly
    parsed_override = parser.parse_args(
        ["-i", "demo.mp4", "--vad", "whisper", "--min-silence", "0.9"]
    )
    overridden = merge_cli_overrides(saved, parsed_override)
    assert overridden.vad_engine == "whisper"
    assert overridden.min_silence_gap == pytest.approx(0.9)
    assert overridden.noise_reduction_method == "spectral"


def test_pyqt6_tune_window_renders_saves_and_resets_offscreen(tmp_path: Path) -> None:
    """Offscreen Qt smoke test verifying schema binding, Apply & Save, IPC reload, and Reset."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from autosilenttrimmer.presentation.tune.tune_window import TuneWindow
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert app is not None

    settings_file = str(tmp_path / "settings.json")
    repo = JsonSettingsRepository(settings_file)
    gateway = _FakeGatewayClient()
    shell = _FakeShell()

    win = TuneWindow(
        settings_repo=repo,
        settings_file_path=settings_file,
        gateway_client=gateway,
        shell_integration=shell,
        shim_executable_path="trim-shim.exe",
    )
    assert win._tabs.count() == len(TUNE_TABS)
    assert set(win._controls.keys()) == set(SETTINGS_BY_KEY.keys())

    # Mutate settings across tabs through UI controls
    win._controls["vad_engine"].setter("energy")
    win._controls["min_silence_gap"].setter(0.42)
    win._controls["x264_preset"].setter("medium")
    win._controls["x264_crf"].setter(21)

    win._apply_btn.click()
    assert gateway.reload_calls == 1
    persisted = repo.load()
    assert persisted.vad_engine == "energy"
    assert persisted.min_silence_gap == pytest.approx(0.42)
    assert persisted.x264_preset == "medium"
    assert persisted.x264_crf == 21

    # Toggle shell integration button from UI
    win._on_toggle_shell()
    assert shell.registered

    # Reset defaults -> verify UI + Save restores canonical values
    win._on_reset_defaults()
    win._apply_btn.click()
    restored = repo.load()
    assert restored.vad_engine == "silero"
    assert restored.x264_crf == 18
    win.close()


def test_ffmpeg_manager_copy_mode_multi_segment_succeeds(golden_mp4: str, tmp_path: Path) -> None:
    """Verify copy_mode=True supports multiple segments without -filter_complex/-c copy failure."""
    from autosilenttrimmer.domain.entities.segment import MediaSegment

    ffmpeg_path = ManagedFFmpegLocator().locate()
    mgr = FFmpegMediaManager(ffmpeg_path)
    out_mp4 = str(tmp_path / "copy_multi.mp4")
    mgr.slice_and_concat(
        media_path=golden_mp4,
        segments=[MediaSegment(0.5, 1.8), MediaSegment(2.5, 3.8)],
        output_path=out_mp4,
        video_encoder="copy",
        copy_mode=True,
    )
    assert os.path.isfile(out_mp4)
    assert os.path.getsize(out_mp4) > 0


def test_ensure_initial_settings_selects_energy_without_torch_and_preserves_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    from autosilenttrimmer.presentation.cli.runtime_builder import ensure_initial_settings

    settings_file = tmp_path / "settings.json"
    repo = JsonSettingsRepository(str(settings_file))

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    lean = ensure_initial_settings(repo, str(settings_file))
    assert lean.vad_engine == "energy"
    assert settings_file.is_file()

    # Once user saves an explicit preference, re-running must never overwrite it
    repo.save(UserSettings(vad_engine="silero"))
    preserved = ensure_initial_settings(repo, str(settings_file))
    assert preserved.vad_engine == "silero"
