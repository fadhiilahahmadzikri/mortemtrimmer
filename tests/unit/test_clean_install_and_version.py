"""Unit tests for clean-install cleaner script and SemVer version single source of truth."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

from autosilenttrimmer.core.constants import APP_VERSION
from autosilenttrimmer.infrastructure.runtime import model_paths as model_paths_mod
from autosilenttrimmer.infrastructure.runtime.model_paths import (
    resolve_offline_deepfilter_dir,
    resolve_offline_silero_dir,
    resolve_offline_whisper_dir,
)
from scripts.clean_install import clean_installed_app


def test_version_ssot_parity_across_pyproject_constants_and_installer() -> None:
    """Keep PEP 621 version, core runtime APP_VERSION, and Inno Setup version identical."""
    root = Path(__file__).resolve().parents[2]
    pyproject_data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    pep_ver = pyproject_data["project"]["version"]

    iss_text = (root / "packaging" / "windows" / "installer.iss").read_text(encoding="utf-8")
    m = re.search(r'#define MyAppVersion "([^"]+)"', iss_text)
    assert m is not None
    iss_ver = m.group(1)

    assert APP_VERSION == pep_ver == iss_ver


def test_clean_installed_app_preserves_logs_by_default_and_purges_when_asked(
    tmp_path: Path,
) -> None:
    install_dir = tmp_path / "Programs" / "AutoSilentTrimmer"
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    menu_dir = tmp_path / "StartMenu"

    install_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    menu_dir.mkdir(parents=True)
    (install_dir / "autosilenttrimmer.exe").write_bytes(b"exe")
    (menu_dir / "Trim This Video.lnk").write_bytes(b"lnk")
    log_file = logs_dir / "app.log"
    log_file.write_text("PRESERVED_LOG_ENTRY\n", encoding="utf-8")

    dry = clean_installed_app(
        install_dir=install_dir,
        data_dir=data_dir,
        start_menu_dir=menu_dir,
        unregister_shell=False,
        purge_data=False,
        dry_run=True,
    )
    assert dry["install_dir_removed"] is True
    assert install_dir.exists()
    assert log_file.exists()

    summary = clean_installed_app(
        install_dir=install_dir,
        data_dir=data_dir,
        start_menu_dir=menu_dir,
        unregister_shell=False,
        purge_data=False,
        dry_run=False,
    )
    assert summary["install_dir_removed"] is True
    assert summary["start_menu_removed"] is True
    assert summary["data_purged"] is False
    assert not install_dir.exists()
    assert not menu_dir.exists()
    assert log_file.read_text(encoding="utf-8") == "PRESERVED_LOG_ENTRY\n"

    purged = clean_installed_app(
        install_dir=install_dir,
        data_dir=data_dir,
        start_menu_dir=menu_dir,
        unregister_shell=False,
        purge_data=True,
        dry_run=False,
    )
    assert purged["data_purged"] is True
    assert not data_dir.exists()


def test_offline_model_path_resolver_hermetic(tmp_path: Path, monkeypatch) -> None:
    """Resolve bundled offline model directories strictly against isolated temp roots."""
    fake_repo = tmp_path / "isolated_repo"
    models_root = fake_repo / "packaging" / "offline_models"
    monkeypatch.delenv("AUTOSILENTTRIMMER_MODELS_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(model_paths_mod, "_PROJECT_ROOT", fake_repo)

    assert resolve_offline_silero_dir() is None
    assert resolve_offline_whisper_dir("tiny") is None
    assert resolve_offline_deepfilter_dir() is None

    (models_root / "silero" / "src").mkdir(parents=True)
    (models_root / "silero" / "hubconf.py").write_text("# silero\n", encoding="utf-8")
    (models_root / "whisper" / "tiny").mkdir(parents=True)
    (models_root / "whisper" / "tiny" / "model.bin").write_bytes(b"0")
    (models_root / "whisper" / "tiny" / "config.json").write_text("{}", encoding="utf-8")
    (models_root / "deepfilter" / "DeepFilterNet3").mkdir(parents=True)
    (models_root / "deepfilter" / "DeepFilterNet3" / "config.ini").write_text("", encoding="utf-8")

    assert resolve_offline_silero_dir() == str(models_root / "silero")
    assert resolve_offline_whisper_dir("tiny") == str(models_root / "whisper" / "tiny")
    assert resolve_offline_deepfilter_dir() == str(models_root / "deepfilter" / "DeepFilterNet3")


def test_env_override_excludes_project_root_fallback(tmp_path: Path, monkeypatch) -> None:
    """AUTOSILENTTRIMMER_MODELS_DIR is an explicit override and must never silently fall back."""
    fake_repo = tmp_path / "repo_with_models"
    (fake_repo / "packaging" / "offline_models" / "silero" / "src").mkdir(parents=True)
    (fake_repo / "packaging" / "offline_models" / "silero" / "hubconf.py").write_text(
        "# repo model\n", encoding="utf-8"
    )
    monkeypatch.setattr(model_paths_mod, "_PROJECT_ROOT", fake_repo)

    empty_override = tmp_path / "empty_override"
    empty_override.mkdir()
    monkeypatch.setenv("AUTOSILENTTRIMMER_MODELS_DIR", str(empty_override))
    assert resolve_offline_silero_dir() is None

    custom_override = tmp_path / "custom_override"
    (custom_override / "silero" / "src").mkdir(parents=True)
    (custom_override / "silero" / "hubconf.py").write_text("# override\n", encoding="utf-8")
    monkeypatch.setenv("AUTOSILENTTRIMMER_MODELS_DIR", str(custom_override))
    assert resolve_offline_silero_dir() == str(custom_override / "silero")
