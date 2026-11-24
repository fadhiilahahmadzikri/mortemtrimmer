"""Resolve pre-staged offline neural model weights bundled inside frozen or dev distributions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _candidate_model_roots() -> list[Path]:
    """Return ordered directories searched for bundled offline models."""
    env_dir = os.environ.get("AUTOSILENTTRIMMER_MODELS_DIR", "").strip()
    if env_dir:
        return [Path(env_dir)]
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass) / "offline_models")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        roots.append(exe_dir / "offline_models")
        roots.append(exe_dir / "_internal" / "offline_models")
    roots.append(_PROJECT_ROOT / "packaging" / "offline_models")
    return roots


def resolve_offline_silero_dir() -> str | None:
    """Return local Silero VAD repo directory containing hubconf.py when bundled offline."""
    for root in _candidate_model_roots():
        silero_dir = root / "silero"
        if (silero_dir / "hubconf.py").is_file() and (silero_dir / "src").is_dir():
            return str(silero_dir)
    return None


def resolve_offline_whisper_dir(model_size: str) -> str | None:
    """Return local CTranslate2 Whisper snapshot directory when pre-bundled offline."""
    for root in _candidate_model_roots():
        model_dir = root / "whisper" / model_size
        if (model_dir / "model.bin").is_file() and (model_dir / "config.json").is_file():
            return str(model_dir)
    return None


def resolve_offline_deepfilter_dir() -> str | None:
    """Return local DeepFilterNet3 checkpoint directory when pre-bundled offline."""
    for root in _candidate_model_roots():
        df_dir = root / "deepfilter" / "DeepFilterNet3"
        if (df_dir / "config.ini").is_file() or (df_dir / "checkpoints").is_dir():
            return str(df_dir)
    return None
