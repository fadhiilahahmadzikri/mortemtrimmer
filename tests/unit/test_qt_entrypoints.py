"""Offscreen unit tests covering PyQt6 desktop entrypoints (qt_app, tune, logs)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import pytest
from autosilenttrimmer.core.constants import APP_NAME, APP_SHORT_NAME, SHELL_CONTEXT_MENU_LABEL
from autosilenttrimmer.core.settings_schema import SETTINGS_SCHEMA, ControlType
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.presentation import qt_app
from autosilenttrimmer.presentation.cli.runner import run_cli
from autosilenttrimmer.presentation.logs import app_entry as logs_entry
from autosilenttrimmer.presentation.theme import (
    PALETTE_HIGHLIGHT_RGB,
    PALETTE_WINDOW_RGB,
    format_error_code_label,
    format_stage_label,
    resolve_asset_path,
)
from autosilenttrimmer.presentation.tune import app_entry as tune_entry

pytestmark = pytest.mark.unit


def _get_offscreen_app():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


def _schedule_quit(app, delay_ms: int = 60) -> None:
    from PyQt6.QtCore import QTimer

    def _close_and_quit() -> None:
        for widget in list(app.topLevelWidgets()):
            widget.close()
        app.quit()

    QTimer.singleShot(delay_ms, _close_and_quit)


def test_apply_dark_palette_sets_expected_theme_colors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify shared gold-and-warm-brown theme applies exact Fusion window and highlight colors."""
    from PyQt6.QtGui import QColor, QPalette

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _get_offscreen_app()
    qt_app.apply_dark_palette(app)

    pal = app.palette()
    assert pal.color(QPalette.ColorRole.Window) == QColor(*PALETTE_WINDOW_RGB)
    assert pal.color(QPalette.ColorRole.Highlight) == QColor(*PALETTE_HIGHLIGHT_RGB)
    assert app.styleSheet() != ""


def test_mortem_branding_and_zero_underscores_in_ui_presentation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ensure product branding, assets, dropdowns, and formatters omit raw underscores."""
    from autosilenttrimmer.presentation.tune.tune_window import TuneWindow
    from PyQt6.QtWidgets import QComboBox

    assert APP_SHORT_NAME == "Mortem"
    assert APP_NAME == "Mortem Primer"
    assert SHELL_CONTEXT_MENU_LABEL == "Trim This Video"
    assert resolve_asset_path("mortem_icon.png") is not None
    assert resolve_asset_path("mortem_tray.png") is not None

    for spec in SETTINGS_SCHEMA:
        assert "_" not in spec.tab
        assert "_" not in spec.group
        assert "_" not in spec.label, f"Underscore leaked into UI label: {spec.label}"
        assert "_" not in spec.description, (
            f"Underscore leaked into description: {spec.description}"
        )
        if spec.control_type == ControlType.CHOICE:
            for choice in spec.choices:
                display = spec.display_for_choice(choice)
                assert "_" not in display, f"Underscore leaked into choice label: {display}"

    assert "_" not in format_stage_label("ANALYZING")
    assert "_" not in format_error_code_label("E_DISK_FULL")

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _get_offscreen_app()
    qt_app.apply_dark_palette(app)
    win = TuneWindow(
        settings_repo=JsonSettingsRepository(str(tmp_path / "settings.json")),
        settings_file_path=str(tmp_path / "settings.json"),
    )
    try:
        assert "Mortem Primer" in win.windowTitle()
        for combo in win.findChildren(QComboBox):
            for idx in range(combo.count()):
                assert "_" not in combo.itemText(idx)
    finally:
        win.close()


def test_run_single_instance_window_raises_existing_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify second call connects via QLocalSocket and returns 0 without recreating window."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QMainWindow

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _get_offscreen_app()
    ipc_name = f"ast_test_single_{uuid.uuid4().hex}"
    created: list[QMainWindow] = []
    second_rc: list[int] = []

    def _factory() -> QMainWindow:
        win = QMainWindow()
        created.append(win)
        return win

    def _launch_second() -> None:
        rc2 = qt_app.run_single_instance_window(ipc_name, _factory)
        second_rc.append(rc2)
        _schedule_quit(app, delay_ms=60)

    QTimer.singleShot(50, _launch_second)
    rc1 = qt_app.run_single_instance_window(ipc_name, _factory)
    app.processEvents()

    assert rc1 == 0
    assert second_rc == [0]
    assert len(created) == 1


def test_run_tune_ui_offscreen_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify run_tune_ui initializes TuneWindow offscreen and shuts down cleanly."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(tune_entry, "_TUNE_IPC_NAME", f"test_tune_{uuid.uuid4().hex}")
    app = _get_offscreen_app()

    settings_path = str(tmp_path / "settings.json")
    repo = JsonSettingsRepository(settings_path)
    _schedule_quit(app, delay_ms=80)
    rc = tune_entry.run_tune_ui(
        settings_repo=repo,
        settings_file_path=settings_path,
    )
    app.processEvents()
    assert rc == 0


def test_run_logs_ui_offscreen_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify run_logs_ui renders persisted app.log lines offscreen and exits 0."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(logs_entry, "_LOGS_IPC_NAME", f"test_logs_{uuid.uuid4().hex}")
    app = _get_offscreen_app()

    log_file = tmp_path / "app.log"
    log_file.write_text("2026-11-24 10:00:00 [INFO] Smoke log line\n", encoding="utf-8")
    _schedule_quit(app, delay_ms=80)
    rc = logs_entry.run_logs_ui(log_file_path=str(log_file))
    app.processEvents()
    assert rc == 0


def test_run_cli_check_readiness_hermetic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify --check CLI readiness entrypoint runs cleanly into isolated app data."""
    local_dir = tmp_path / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(local_dir))

    try:
        rc = run_cli(["--check"])
    finally:
        for handler in list(logging.getLogger().handlers):
            handler.close()
            logging.getLogger().removeHandler(handler)

    captured = capsys.readouterr()
    assert rc == 0
    assert "READY FOR INFERENCE" in captured.out
