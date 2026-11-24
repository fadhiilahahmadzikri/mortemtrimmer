"""Stage and SHA-256-verify offline Silero, Whisper, and DeepFilterNet3 weights."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from autosilenttrimmer.core.constants import DEFAULT_SILERO_MODEL_NAME, DEFAULT_SILERO_REPO
from autosilenttrimmer.infrastructure.runtime.pack_manager import compute_sha256

SILERO_PINNED_TAG = "v6.2"
SILERO_PINNED_REPO = f"{DEFAULT_SILERO_REPO}:{SILERO_PINNED_TAG}"
TARGET_ROOT = PROJECT_ROOT / "packaging" / "offline_models"
MANIFEST_PATH = PROJECT_ROOT / "packaging" / "offline_models.manifest.json"
MODEL_SUBDIRS: dict[str, str] = {
    "silero": "silero",
    "deepfilter_DeepFilterNet3": "deepfilter/DeepFilterNet3",
    "whisper_tiny": "whisper/tiny",
    "whisper_base": "whisper/base",
}
_FORBIDDEN_SUFFIXES = (".log", ".pyc")


def _copy_tree_clean(src: Path, dst: Path, *, ignore_names: set[str] | None = None) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    skip = ignore_names or set()
    shutil.copytree(
        src,
        dst,
        symlinks=False,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "*.log", *skip),
    )


def stage_silero(target_root: Path) -> Path:
    """Stage pinned Silero VAD tag without example/test/cache bloat."""
    import torch

    hub_dir = Path(torch.hub.get_dir()) / f"snakers4_silero-vad_{SILERO_PINNED_TAG}"
    if not (hub_dir / "hubconf.py").is_file():
        torch.hub.load(
            repo_or_dir=SILERO_PINNED_REPO,
            model=DEFAULT_SILERO_MODEL_NAME,
            force_reload=False,
            trust_repo=True,
        )

    dst = target_root / MODEL_SUBDIRS["silero"]
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for fname in ("hubconf.py", "LICENSE", "pyproject.toml", "README.md"):
        src_file = hub_dir / fname
        if src_file.is_file():
            shutil.copy2(src_file, dst / fname)
    _copy_tree_clean(hub_dir / "src", dst / "src")
    return dst


def stage_deepfilter(target_root: Path) -> Path:
    """Stage DeepFilterNet3 model directory cleanly excluding runtime log files."""
    from df.enhance import DEFAULT_MODEL, get_model_basedir, init_df

    src_dir = Path(get_model_basedir(DEFAULT_MODEL))
    if not (src_dir / "config.ini").is_file():
        init_df(config_allow_defaults=True, log_file=None)
        src_dir = Path(get_model_basedir(DEFAULT_MODEL))
    dst = target_root / MODEL_SUBDIRS["deepfilter_DeepFilterNet3"]
    _copy_tree_clean(src_dir, dst, ignore_names={"enhance.log"})
    return dst


def stage_whisper_models(
    target_root: Path, sizes: tuple[str, ...] = ("tiny", "base")
) -> list[Path]:
    """Download/resolve Faster-Whisper CTranslate2 snapshots as standalone local folders."""
    from faster_whisper.utils import download_model

    staged: list[Path] = []
    for size in sizes:
        snapshot_dir = Path(download_model(size))
        dst = target_root / MODEL_SUBDIRS[f"whisper_{size}"]
        _copy_tree_clean(snapshot_dir, dst, ignore_names={".locks"})
        staged.append(dst)
    return staged


def build_manifest_payload(target_root: Path) -> dict[str, Any]:
    """Scan staged model directories and compute deterministic SHA-256 inventory."""
    models: dict[str, Any] = {}
    for key, rel_dir in MODEL_SUBDIRS.items():
        model_dir = target_root / rel_dir
        if not model_dir.is_dir():
            raise FileNotFoundError(f"Missing staged model directory: {model_dir}")
        files: dict[str, dict[str, Any]] = {}
        for path in sorted(model_dir.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file():
                continue
            if path.suffix.lower() in _FORBIDDEN_SUFFIXES:
                raise RuntimeError(f"Refusing to include runtime artifact in manifest: {path}")
            rel_path = path.relative_to(model_dir).as_posix()
            files[rel_path] = {
                "sha256": compute_sha256(str(path)),
                "size_bytes": path.stat().st_size,
            }
        models[key] = {"relative_dir": rel_dir, "files": files}
    return {
        "schema_version": "1.0",
        "silero_tag": SILERO_PINNED_TAG,
        "models": models,
    }


def write_manifest(target_root: Path, manifest_path: Path) -> dict[str, Any]:
    """Write deterministic SHA-256 manifest JSON for staged offline models."""
    payload = build_manifest_payload(target_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return payload


def verify_manifest(target_root: Path, manifest_path: Path) -> None:
    """Validate staged offline model files match pinned SHA-256 hashes and sizes strictly."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing pinned offline model manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    models = manifest.get("models", {})
    if not models:
        raise RuntimeError(f"Offline model manifest contains zero models: {manifest_path}")

    for key, spec in models.items():
        rel_dir = spec["relative_dir"]
        expected_files: dict[str, dict[str, Any]] = spec["files"]
        model_dir = target_root / rel_dir
        if not model_dir.is_dir():
            raise FileNotFoundError(f"Missing model directory for {key}: {model_dir}")

        actual_rel_paths = {
            p.relative_to(model_dir).as_posix() for p in model_dir.rglob("*") if p.is_file()
        }
        forbidden = [p for p in actual_rel_paths if p.lower().endswith(_FORBIDDEN_SUFFIXES)]
        if forbidden:
            raise RuntimeError(f"Forbidden runtime files present in {key}: {forbidden}")
        if set(expected_files.keys()) != actual_rel_paths:
            missing = sorted(set(expected_files.keys()) - actual_rel_paths)
            extra = sorted(actual_rel_paths - set(expected_files.keys()))
            raise RuntimeError(f"Manifest file mismatch in {key}: missing={missing}, extra={extra}")
        for rel_path, meta in expected_files.items():
            file_path = model_dir / rel_path
            actual_size = file_path.stat().st_size
            if actual_size != meta["size_bytes"]:
                raise RuntimeError(
                    f"Size mismatch for {key}/{rel_path}: {actual_size} != {meta['size_bytes']}"
                )
            actual_sha = compute_sha256(str(file_path))
            if actual_sha != meta["sha256"]:
                raise RuntimeError(
                    f"SHA-256 mismatch for {key}/{rel_path}: {actual_sha} != {meta['sha256']}"
                )


def main(argv: list[str] | None = None) -> int:
    """Stage and SHA-256-verify all neural checkpoints for 100% offline builds."""
    parser = argparse.ArgumentParser(description="Stage and verify pinned offline AI weights.")
    parser.add_argument(
        "--verify", action="store_true", help="Verify staged weights against manifest only."
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="Stage fresh weights and regenerate packaging/offline_models.manifest.json.",
    )
    parser.add_argument(
        "--force-restage",
        action="store_true",
        help="Force clean re-staging even if existing files verify cleanly.",
    )
    args = parser.parse_args(argv)

    if args.verify:
        verify_manifest(TARGET_ROOT, MANIFEST_PATH)
        print(f"Verified offline models against {MANIFEST_PATH}")
        return 0

    if not args.write_manifest and not args.force_restage and MANIFEST_PATH.is_file():
        try:
            verify_manifest(TARGET_ROOT, MANIFEST_PATH)
            total_mb = (
                sum(f.stat().st_size for f in TARGET_ROOT.rglob("*") if f.is_file()) / 1048576
            )
            print(f"Offline models already staged and SHA-256 verified ({total_mb:.2f} MB)")
            return 0
        except (FileNotFoundError, RuntimeError):
            pass

    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    silero_dst = stage_silero(TARGET_ROOT)
    df_dst = stage_deepfilter(TARGET_ROOT)
    whisper_dsts = stage_whisper_models(TARGET_ROOT)

    if args.write_manifest:
        write_manifest(TARGET_ROOT, MANIFEST_PATH)
        print(f"Wrote SHA-256 manifest: {MANIFEST_PATH}")

    verify_manifest(TARGET_ROOT, MANIFEST_PATH)

    total_mb = sum(f.stat().st_size for f in TARGET_ROOT.rglob("*") if f.is_file()) / 1048576
    print(f"Staged Silero       : {silero_dst} ({SILERO_PINNED_TAG})")
    print(f"Staged DeepFilter3  : {df_dst}")
    for w in whisper_dsts:
        print(f"Staged Whisper      : {w}")
    print(f"Total offline weights staged & verified: {total_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
