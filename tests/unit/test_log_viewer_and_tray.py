"""Unit and offscreen Qt tests for preserved logs, LogViewerWindow, and non-silent failures."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest
from autosilenttrimmer.application.use_cases.job_orchestrator import JobOrchestrator
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.contracts.compute import ICapabilityProber, IComputeBackend
from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.media_prober import IMediaProber
from autosilenttrimmer.domain.contracts.media_verifier import IMediaVerifier, VerificationReport
from autosilenttrimmer.domain.contracts.notifier import INotifier
from autosilenttrimmer.domain.contracts.trim_strategy import ITrimStrategy
from autosilenttrimmer.domain.contracts.ui import ITrayUI
from autosilenttrimmer.domain.models.compute import (
    BackendSelection,
    ComputeCapabilities,
    ComputePolicy,
    PlatformSpec,
)
from autosilenttrimmer.domain.models.events import JobFailed, ProgressUpdated
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo, StreamSummary
from autosilenttrimmer.domain.models.processing_command import ProcessMediaCommand
from autosilenttrimmer.infrastructure.events.in_memory_bus import InMemoryEventBus
from autosilenttrimmer.infrastructure.notify.composite_notifier import CompositeNotifier
from autosilenttrimmer.infrastructure.notify.desktop_notifier_adapter import DesktopNotifierAdapter
from autosilenttrimmer.presentation.cli.parser import build_argument_parser
from autosilenttrimmer.presentation.cli.runner import configure_logging


class _DummyTray(ITrayUI):
    def __init__(self) -> None:
        self.balloons: list[tuple[str, str]] = []

    def start(self, **kwargs: object) -> None:
        pass

    def show_balloon(self, title: str, message: str) -> None:
        self.balloons.append((title, message))

    def stop(self) -> None:
        pass


class _SilentPrimaryNotifier(INotifier):
    def notify_completed(self, *args: object) -> None:
        pass

    def notify_failed(self, source_path: str, error_code: str, message: str) -> None:
        # Simulates OS toast returning quietly without error even when suppressed by Windows
        return

    def notify_info(self, title: str, message: str) -> None:
        pass


class _FakeGateway(IJobGatewayClient):
    def __init__(self, alive: bool = True) -> None:
        self._alive = alive

    def is_daemon_running(self) -> bool:
        return self._alive

    def enqueue_paths(self, paths: list[str]) -> bool:
        return True

    def notify_settings_updated(self) -> bool:
        return True


def test_configure_logging_preserves_existing_log_entries(tmp_path: Path) -> None:
    """Calling configure_logging repeatedly must strictly append and retain historical entries."""
    log_file = tmp_path / "app.log"
    historical = "2026-11-24 20:00:00,000 [INFO] HISTORICAL_ENTRY_MUST_SURVIVE\n"
    log_file.write_text(historical, encoding="utf-8")

    try:
        configure_logging(str(tmp_path))
        logging.getLogger("autosilenttrimmer.test").info("SECOND_SESSION_ENTRY")
        configure_logging(str(tmp_path))
        logging.getLogger("autosilenttrimmer.test").error("THIRD_SESSION_ERROR")
        logging.shutdown()

        text = log_file.read_text(encoding="utf-8")
        assert text.startswith(historical)
        assert "SECOND_SESSION_ENTRY" in text
        assert "THIRD_SESSION_ERROR" in text
    finally:
        logging.basicConfig(handlers=[], force=True)


def test_composite_notifier_and_desktop_adapter_never_suppress_failure() -> None:
    l10n = Localizer("en")
    tray = _DummyTray()
    comp = CompositeNotifier(_SilentPrimaryNotifier(), l10n, tray_ui=tray)
    comp.notify_failed("clip.mp4", "E_DEPENDENCY_MISSING", "Missing PyTorch")
    assert len(tray.balloons) == 1
    assert "E_DEPENDENCY_MISSING" in tray.balloons[0][0]
    assert "Missing PyTorch" in tray.balloons[0][1]

    adapter = DesktopNotifierAdapter(l10n, enabled=True)
    adapter._notifier = None
    with pytest.raises(RuntimeError, match="unavailable"):
        adapter.notify_failed("clip.mp4", "E_VERIFY_FAILED", "Mismatch")


def test_pyqt6_log_viewer_preserves_logs_filters_and_tails_offscreen(tmp_path: Path) -> None:
    """Offscreen Qt LogViewerWindow reads preserved entries non-destructively and auto-refreshes."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from autosilenttrimmer.presentation.logs.log_viewer import LogViewerWindow
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert app is not None

    log_file = tmp_path / "app.log"
    initial_lines = (
        "2026-11-24 21:18:55,000 [INFO] [pid:100] IPC batch dispatched (1 file)\n"
        "2026-11-24 21:19:03,000 [WARNING] [pid:100] Legacy warning check\n"
        "2026-11-24 21:19:06,000 [ERROR] [pid:100] PyTorch missing for Silero VAD\n"
    )
    log_file.write_text(initial_lines, encoding="utf-8")
    before_bytes = log_file.read_bytes()

    win = LogViewerWindow(log_file_path=str(log_file), gateway_client=_FakeGateway(alive=True))
    assert "Running" in win._daemon_lbl.text()
    assert "Latest Error (1 total):" in win._error_banner.text()
    assert "HISTORICAL" not in win._text_view.toPlainText()
    assert "PyTorch missing" in win._text_view.toPlainText()
    assert log_file.read_bytes() == before_bytes

    # Filter Errors level cleanly in memory without touching disk log
    win._level_combo.setCurrentText("Errors")
    rendered = win._text_view.toPlainText()
    assert "PyTorch missing" in rendered
    assert "IPC batch" not in rendered
    assert log_file.read_bytes() == before_bytes

    # Append a new line on disk and confirm refresh picks it up while keeping prior history
    win._level_combo.setCurrentText("All Levels")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("2026-11-24 21:25:00,000 [INFO] [pid:100] New trimmed output ready\n")
    win.refresh_logs(force=True)
    full_view = win._text_view.toPlainText()
    assert "IPC batch dispatched" in full_view
    assert "PyTorch missing" in full_view
    assert "New trimmed output ready" in full_view
    win.close()


def test_job_orchestrator_emits_early_progress_and_handles_failure_visibly(
    tmp_path: Path,
) -> None:
    """Confirm JobStarted/PROBING triggers early ProgressUpdated and failures reach tray/bus."""

    class _FakeMedia(IMediaManager):
        def extract_audio(self, s: str, d: str) -> None:
            raise RuntimeError("boom during extract")

        def slice_and_concat(self, *args: object, **kwargs: object) -> None:
            pass

        def concat_files(self, *args: object, **kwargs: object) -> None:
            pass

        def merge_audio(self, *args: object, **kwargs: object) -> None:
            pass

        def export_audio(self, *args: object, **kwargs: object) -> None:
            pass

    class _FakeProber(IMediaProber):
        def probe(self, media_path: str) -> MediaProbeInfo:
            return MediaProbeInfo(
                path=media_path,
                container_format="mp4",
                extension=".mp4",
                duration_sec=10.0,
                file_size_bytes=1024,
                is_video=True,
                video_streams=(StreamSummary(index=0, media_type="video", codec_name="h264"),),
            )

    class _FakeVerifier(IMediaVerifier):
        def verify(self, *args: object, **kwargs: object) -> VerificationReport:
            return VerificationReport(True, 5.0, 5.0, True, 2)

    class _FakeStrategy(ITrimStrategy):
        @property
        def strategy_id(self) -> str:
            return "auto-silence"

        @property
        def requires_frame_accuracy(self) -> bool:
            return True

        def plan_keep_segments(self, *args: object, **kwargs: object) -> list:
            return []

    class _FakeCapProber(ICapabilityProber):
        def probe(self, force_refresh: bool = False) -> ComputeCapabilities:
            return ComputeCapabilities(
                PlatformSpec("windows", "x86_64"), 4, 2, 1024**3, 1024**3, "cpu", ()
            )

    class _FakeBackend(IComputeBackend):
        def select_backend(self, policy: ComputePolicy, ffmpeg_path: str, req: int | None = None):
            return BackendSelection("cpu", "cpu", "libx264", 1, False, "cpu")

        def fallback_to_cpu(self, reason: str) -> BackendSelection:
            return BackendSelection("cpu", "cpu", "libx264", 1, False, reason)

    bus = InMemoryEventBus()
    progress: list[ProgressUpdated] = []
    failed: list[JobFailed] = []
    bus.subscribe(ProgressUpdated, lambda ev: progress.append(ev))  # type: ignore[arg-type]
    bus.subscribe(JobFailed, lambda ev: failed.append(ev))  # type: ignore[arg-type]
    tray = _DummyTray()
    notifier = CompositeNotifier(_SilentPrimaryNotifier(), Localizer("en"), tray_ui=tray)

    sample = tmp_path / "broken.mp4"
    sample.write_bytes(b"0" * 100)
    orch = JobOrchestrator(
        media_manager=_FakeMedia(),
        media_prober=_FakeProber(),
        media_verifier=_FakeVerifier(),
        trim_strategy=_FakeStrategy(),
        capability_prober=_FakeCapProber(),
        compute_backend=_FakeBackend(),
        event_bus=bus,
        notifier=notifier,
    )
    with pytest.raises(RuntimeError, match="boom during extract"):
        orch.execute_job(ProcessMediaCommand(input_path=str(sample)))

    assert any(ev.percent == 5.0 and ev.backend_label == "PROBING" for ev in progress)
    assert any(ev.percent == 12.0 and ev.backend_label == "ANALYZING" for ev in progress)
    assert len(failed) == 1
    assert len(tray.balloons) == 1
    assert "boom during extract" in tray.balloons[0][1]


def test_parser_accepts_logs_flag() -> None:
    parsed = build_argument_parser().parse_args(["--logs"])
    assert parsed.logs is True
