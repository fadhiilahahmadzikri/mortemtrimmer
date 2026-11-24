"""Unit tests for ComputePolicy G1/G2/G3, Ed25519 manifest signing, and RuntimePack rollback."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from autosilenttrimmer.core.exceptions import ComputeBackendException, ManifestValidationException
from autosilenttrimmer.domain.contracts.compute import ICapabilityProber
from autosilenttrimmer.domain.models.compute import (
    ComputeCapabilities,
    ComputePolicy,
    PlatformSpec,
)
from autosilenttrimmer.domain.models.runtime_pack import RuntimePackArtifact
from autosilenttrimmer.infrastructure.compute.backend_selector import PolicyComputeBackend
from autosilenttrimmer.infrastructure.runtime.pack_manager import (
    ManagedRuntimePackManager,
    compute_sha256,
)
from scripts.sign_manifest import generate_keypair, sign_manifest


class _FakeProber(ICapabilityProber):
    def __init__(self, caps: ComputeCapabilities) -> None:
        self._caps = caps

    def probe(self, force_refresh: bool = False) -> ComputeCapabilities:
        return self._caps


def test_compute_policy_g1_g2_g3_behavior() -> None:
    cpu_only_caps = ComputeCapabilities(
        platform_spec=PlatformSpec("windows", "x86_64"),
        logical_cores=8,
        physical_cores=4,
        total_ram_bytes=8 * 1024**3,
        available_ram_bytes=4 * 1024**3,
        ai_device="cpu",
        hw_video_encoders=(),
    )
    selector = PolicyComputeBackend(_FakeProber(cpu_only_caps))

    with pytest.raises(ComputeBackendException):
        selector.select_backend(ComputePolicy.G1_HARD_GATE, "ffmpeg")

    g2_sel = selector.select_backend(ComputePolicy.G2_GPU_PREFERRED, "ffmpeg")
    assert not g2_sel.is_gpu
    assert g2_sel.video_encoder == "libx264"

    nvenc_caps = ComputeCapabilities(
        platform_spec=PlatformSpec("windows", "x86_64"),
        logical_cores=8,
        physical_cores=4,
        total_ram_bytes=8 * 1024**3,
        available_ram_bytes=4 * 1024**3,
        ai_device="cpu",
        hw_video_encoders=("h264_nvenc", "h264_qsv"),
    )
    gpu_selector = PolicyComputeBackend(_FakeProber(nvenc_caps))
    picked = gpu_selector.select_backend(ComputePolicy.G2_GPU_PREFERRED, "ffmpeg")
    assert picked.is_gpu
    assert picked.video_encoder == "h264_nvenc"

    g3_sel = gpu_selector.select_backend(ComputePolicy.G3_CPU_ONLY, "ffmpeg")
    assert not g3_sel.is_gpu
    assert g3_sel.video_encoder == "libx264"


def test_ed25519_signed_manifest_and_tamper_rejection(tmp_path: Path) -> None:
    priv_p, pub_p = generate_keypair(str(tmp_path / "keys"))
    priv_hex = Path(priv_p).read_text(encoding="utf-8")
    pub_hex = Path(pub_p).read_text(encoding="utf-8")

    # Build dummy runtime pack zip
    pack_zip = tmp_path / "ffmpeg-windows-x86_64-7.1.0.zip"
    with zipfile.ZipFile(pack_zip, "w") as zf:
        zf.writestr("bin/ffmpeg.exe", b"dummy-binary-payload")
    good_sha = compute_sha256(str(pack_zip))

    manifest_file = tmp_path / "release-manifest.json"
    manifest_data = {
        "schema_version": "1.0",
        "app_version": "1.0.0",
        "channels": {
            "stable": {
                "installers": {},
                "runtime_packs": {
                    "ffmpeg-windows-x86_64": {
                        "pack_type": "ffmpeg",
                        "platform_tag": "windows-x86_64",
                        "version": "7.1.0",
                        "url": str(pack_zip),
                        "sha256": good_sha,
                        "size_bytes": pack_zip.stat().st_size,
                    }
                },
            }
        },
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    sign_manifest(str(manifest_file), priv_hex)

    mgr = ManagedRuntimePackManager(
        runtime_packs_dir=str(tmp_path / "packs"),
        cache_dir=str(tmp_path / "cache"),
        public_key_hex=pub_hex,
    )
    parsed = mgr.fetch_manifest(str(manifest_file))
    assert "ffmpeg-windows-x86_64" in parsed.runtime_packs

    # Tamper manifest version without re-signing -> must reject
    tampered = json.loads(manifest_file.read_text(encoding="utf-8"))
    tampered["app_version"] = "9.9.9"
    manifest_file.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ManifestValidationException):
        mgr.fetch_manifest(str(manifest_file))

    # Wrong SHA-256 on offline pack install -> reject cleanly
    with pytest.raises(ManifestValidationException):
        mgr.install_local_pack(str(pack_zip), expected_sha256="0" * 64, pack_id="bad-pack")

    # Valid offline install + clean uninstall
    rec = mgr.install_local_pack(str(pack_zip), expected_sha256=good_sha, pack_id="good-pack")
    assert Path(rec.install_dir, "bin", "ffmpeg.exe").is_file()
    mgr.rollback_or_uninstall("good-pack")
    assert mgr.list_installed() == []
    assert not Path(rec.install_dir).exists()


def test_runtime_pack_selector_picks_host_os_arch(tmp_path: Path) -> None:
    mgr = ManagedRuntimePackManager(
        runtime_packs_dir=str(tmp_path / "packs"),
        cache_dir=str(tmp_path / "cache"),
    )
    from autosilenttrimmer.domain.models.runtime_pack import ReleaseManifest

    manifest = ReleaseManifest(
        schema_version="1.0",
        app_version="1.0.0",
        channel="stable",
        runtime_packs={
            "ffmpeg-windows-x86_64": RuntimePackArtifact(
                pack_id="ffmpeg-windows-x86_64",
                pack_type="ffmpeg",
                platform_tag="windows-x86_64",
                version="7.1.0",
                url="https://example.invalid/win.zip",
                sha256="abc",
            ),
            "ffmpeg-darwin-arm64": RuntimePackArtifact(
                pack_id="ffmpeg-darwin-arm64",
                pack_type="ffmpeg",
                platform_tag="darwin-arm64",
                version="7.1.0",
                url="https://example.invalid/mac.zip",
                sha256="def",
            ),
            "ai-cpu-windows-x86_64": RuntimePackArtifact(
                pack_id="ai-cpu-windows-x86_64",
                pack_type="ai-cpu",
                platform_tag="windows-x86_64",
                version="1.0.0",
                url="https://example.invalid/cpu.zip",
                sha256="ghi",
            ),
        },
    )
    win_spec = PlatformSpec("windows", "x86_64")
    caps = ComputeCapabilities(
        platform_spec=win_spec,
        logical_cores=4,
        physical_cores=2,
        total_ram_bytes=8 * 1024**3,
        available_ram_bytes=4 * 1024**3,
        ai_device="cpu",
    )
    selected = mgr.select_packs_for_host(manifest, win_spec, caps)
    assert [p.pack_id for p in selected] == ["ffmpeg-windows-x86_64", "ai-cpu-windows-x86_64"]
