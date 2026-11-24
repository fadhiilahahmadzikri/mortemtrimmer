# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Unit tests enforcing single-source branding, SPDX/metadata parity, and Qt UI attribution."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from autosilenttrimmer import branding
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.presentation import about_entry, qt_app
from autosilenttrimmer.presentation.about_dialog import AboutDialog, ThirdPartyNoticesDialog
from autosilenttrimmer.presentation.cli.runner import run_cli
from autosilenttrimmer.presentation.logs.log_viewer import LogViewerWindow
from autosilenttrimmer.presentation.theme import render_github_icon, resolve_asset_path
from autosilenttrimmer.presentation.tune.tune_window import TuneWindow

pytestmark = pytest.mark.unit


def _get_offscreen_app():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


def test_branding_ssot_consistency_across_repo_metadata() -> None:
    """Verify branding.py, pyproject.toml, installer.iss, LICENSE, and CITATION.cff match."""
    root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    proj = pyproject["project"]

    assert proj["version"] == branding.APP_VERSION
    assert proj["license"] == branding.SPDX_LICENSE_ID
    assert proj["authors"][0]["name"] == branding.AUTHOR
    assert proj["urls"]["Homepage"] == branding.GITHUB_URL
    assert proj["urls"]["Repository"] == branding.GITHUB_URL
    assert proj["urls"]["Issues"] == branding.GITHUB_ISSUES_URL

    iss = (root / "packaging" / "windows" / "installer.iss").read_text(encoding="utf-8")
    expected_iss = {
        "MyAppName": branding.APP_NAME,
        "MyAppPublisher": branding.AUTHOR,
        "MyAppPublisherURL": branding.GITHUB_PROFILE_URL,
        "MyAppURL": branding.GITHUB_URL,
        "MyAppSupportURL": branding.GITHUB_ISSUES_URL,
        "MyAppCopyright": branding.COPYRIGHT_NOTICE,
        "MyAppVersion": branding.APP_VERSION,
    }
    for macro, expected in expected_iss.items():
        m = re.search(rf'#define {macro} "([^"]+)"', iss)
        assert m is not None and m.group(1) == expected, f"Mismatch in installer.iss macro {macro}"

    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert branding.COPYRIGHT_NOTICE in license_text

    cff_text = (root / "CITATION.cff").read_text(encoding="utf-8")
    assert branding.GITHUB_URL in cff_text
    assert f"version: {branding.APP_VERSION}" in cff_text
    assert "Zikri" in cff_text


def test_about_dialog_and_github_icon_attribution_offscreen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify AboutDialog content, GitHub QDesktopServices call, and light/dark Octicon tint."""
    from PyQt6.QtGui import QColor, QDesktopServices

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    opened_urls: list[str] = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened_urls.append(url.toString()) or True
    )

    app = _get_offscreen_app()
    qt_app.apply_dark_palette(app)

    assert resolve_asset_path("github_mark.svg") is not None
    assert not render_github_icon(QColor("#F4EAD5"), 16).pixmap(16, 16).isNull()
    assert not render_github_icon(QColor("#1C1613"), 16).pixmap(16, 16).isNull()

    dlg = AboutDialog()
    try:
        assert dlg.icon_label.pixmap() is not None and not dlg.icon_label.pixmap().isNull()
        assert branding.APP_NAME in dlg.title_label.text()
        assert branding.APP_VERSION in dlg.version_label.text()
        assert branding.ATTRIBUTION_LINE in dlg.author_label.text()
        assert branding.COPYRIGHT_NOTICE in dlg.copyright_label.text()
        assert branding.GITHUB_URL in dlg.github_btn.text()
        assert branding.LICENSE_NAME in dlg.license_label.text()

        dlg.github_btn.click()
        assert opened_urls == [branding.GITHUB_URL]

        notices_dlg = ThirdPartyNoticesDialog(dlg)
        assert branding.APP_NAME in notices_dlg.windowTitle()
        notices_dlg.close()
    finally:
        dlg.close()


def test_gui_windows_include_help_menu_github_button_and_attribution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify TuneWindow and LogViewerWindow expose Help menu, GitHub icon, and author label."""
    from PyQt6.QtGui import QDesktopServices

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    opened_urls: list[str] = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened_urls.append(url.toString()) or True
    )

    app = _get_offscreen_app()
    qt_app.apply_dark_palette(app)

    settings_file = str(tmp_path / "settings.json")
    tune_win = TuneWindow(
        settings_repo=JsonSettingsRepository(settings_file),
        settings_file_path=settings_file,
    )
    log_file = tmp_path / "app.log"
    log_file.write_text("2026-11-24 12:00:00 [INFO] Entry\n", encoding="utf-8")
    log_win = LogViewerWindow(log_file_path=str(log_file))

    try:
        for win in (tune_win, log_win):
            assert win._attribution_lbl.text() == branding.ATTRIBUTION_LINE
            assert win._github_btn.toolTip() == branding.GITHUB_HANDLE
            win._github_btn.click()

            help_actions = [a for a in win.menuBar().actions() if a.text() == "Help"]
            assert len(help_actions) == 1
            sub_actions = {a.text(): a for a in help_actions[0].menu().actions()}
            assert "About" in sub_actions
            assert "GitHub Repository" in sub_actions
            sub_actions["GitHub Repository"].trigger()

        assert opened_urls == [branding.GITHUB_URL] * 4
    finally:
        tune_win.close()
        log_win.close()


def test_cli_version_and_about_entrypoint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify autosilenttrimmer-cli --version and offscreen --about launcher."""
    from PyQt6.QtCore import QTimer

    rc = run_cli(["--version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert branding.APP_NAME in out
    assert branding.APP_VERSION in out
    assert branding.AUTHOR in out
    assert branding.COPYRIGHT_NOTICE in out
    assert branding.GITHUB_URL in out

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _get_offscreen_app()
    QTimer.singleShot(60, lambda: [w.close() for w in list(app.topLevelWidgets())] and app.quit())
    assert about_entry.run_about_ui() == 0
