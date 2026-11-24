"""Signed, hash-verified, atomic Runtime Pack lifecycle manager (Doc 02 §5.2-5.3)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import zipfile
from dataclasses import asdict
from typing import Any

from autosilenttrimmer.core.constants import DEFAULT_RELEASE_CHANNEL, RUNTIME_PUBLIC_KEY_ENV
from autosilenttrimmer.core.exceptions import ErrorCode, ManifestValidationException
from autosilenttrimmer.domain.contracts.runtime_manager import IRuntimeManager
from autosilenttrimmer.domain.models.compute import ComputeCapabilities, PlatformSpec
from autosilenttrimmer.domain.models.runtime_pack import (
    InstalledPackRecord,
    ReleaseManifest,
    RuntimePackArtifact,
)
from autosilenttrimmer.infrastructure.runtime.manifest_client import HttpManifestClient
from autosilenttrimmer.infrastructure.runtime.runtime_injector import activate_runtime_pack
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_manifest_bytes(raw_manifest: dict[str, Any]) -> bytes:
    """Produce deterministic canonical JSON bytes excluding signature field for Ed25519."""
    body = {k: v for k, v in raw_manifest.items() if k != "signature_ed25519"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_ed25519_hex(payload: bytes, signature_hex: str, public_key_hex: str) -> None:
    """Validate Ed25519 signature raising ManifestValidationException on tamper."""
    if not signature_hex:
        raise ManifestValidationException(
            "Missing cryptographic signature on artifact or manifest.",
            code=ErrorCode.MANIFEST_INVALID,
        )
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pub.verify(bytes.fromhex(signature_hex), payload)
    except (ValueError, InvalidSignature) as exc:
        raise ManifestValidationException(
            f"Cryptographic signature verification failed: {exc}",
            code=ErrorCode.MANIFEST_INVALID,
        ) from exc


def compute_sha256(file_path: str) -> str:
    """Compute lowercase hexadecimal SHA-256 checksum for a file."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class ManagedRuntimePackManager(IRuntimeManager):
    """Installs, verifies, activates, and rolls back isolated OS-agnostic runtime packs."""

    REGISTRY_FILENAME = "installed_packs.json"

    def __init__(
        self,
        runtime_packs_dir: str,
        cache_dir: str,
        manifest_client: HttpManifestClient | None = None,
        public_key_hex: str | None = None,
    ) -> None:
        self._packs_dir = runtime_packs_dir
        self._cache_dir = cache_dir
        self._client = manifest_client or HttpManifestClient()
        self._public_key_hex = public_key_hex or os.environ.get(RUNTIME_PUBLIC_KEY_ENV)
        os.makedirs(self._packs_dir, exist_ok=True)
        os.makedirs(self._cache_dir, exist_ok=True)

    def fetch_manifest(
        self, manifest_url: str, channel: str = DEFAULT_RELEASE_CHANNEL
    ) -> ReleaseManifest:
        """Download release manifest and verify Ed25519 signature when public key is set."""
        raw = self._client.fetch_raw_manifest(manifest_url)
        if self._public_key_hex:
            verify_ed25519_hex(
                canonical_manifest_bytes(raw),
                str(raw.get("signature_ed25519", "")),
                self._public_key_hex,
            )
        return self._client.parse_manifest(raw, channel=channel)

    def select_packs_for_host(
        self,
        manifest: ReleaseManifest,
        platform_spec: PlatformSpec,
        capabilities: ComputeCapabilities,
    ) -> list[RuntimePackArtifact]:
        """Select matching FFmpeg and AI CPU/GPU packs for normalized OS/arch (Doc 02 §5.3)."""
        tag = platform_spec.platform_tag
        candidates = [p for p in manifest.runtime_packs.values() if p.platform_tag == tag]
        selected: list[RuntimePackArtifact] = []

        ffmpeg_packs = [p for p in candidates if p.pack_type == "ffmpeg"]
        if ffmpeg_packs:
            selected.append(ffmpeg_packs[0])

        gpu_vendors = {g.vendor for g in capabilities.gpu_adapters if g.supports_cuda}
        cuda_packs = [p for p in candidates if p.requires_gpu and p.vendor in gpu_vendors]
        cpu_packs = [p for p in candidates if p.pack_type == "ai-cpu"]

        if cuda_packs:
            selected.append(cuda_packs[0])
        elif cpu_packs:
            selected.append(cpu_packs[0])

        return selected

    def install_pack(self, artifact: RuntimePackArtifact) -> InstalledPackRecord:
        """Download pack with resume, verify SHA-256 + optional Ed25519, install atomically."""
        archive_path = os.path.join(self._cache_dir, f"{artifact.pack_id}-{artifact.version}.zip")
        self._client.download_resumable(
            artifact.pack_id,
            artifact.url,
            archive_path,
            expected_total_bytes=artifact.size_bytes,
        )
        return self._verify_and_extract(
            pack_id=artifact.pack_id,
            version=artifact.version,
            archive_path=archive_path,
            expected_sha256=artifact.sha256,
            signature_hex=artifact.signature_ed25519,
            delete_on_mismatch=True,
        )

    def install_local_pack(
        self,
        archive_path: str,
        expected_sha256: str,
        pack_id: str = "offline-pack",
        version: str = "local",
    ) -> InstalledPackRecord:
        """Offline installation flow for bundled archives."""
        return self._verify_and_extract(
            pack_id=pack_id,
            version=version,
            archive_path=archive_path,
            expected_sha256=expected_sha256,
            signature_hex="",
            delete_on_mismatch=False,
        )

    def _verify_and_extract(
        self,
        *,
        pack_id: str,
        version: str,
        archive_path: str,
        expected_sha256: str,
        signature_hex: str,
        delete_on_mismatch: bool = False,
    ) -> InstalledPackRecord:
        actual_sha = compute_sha256(archive_path)
        if actual_sha.lower() != expected_sha256.lower():
            if delete_on_mismatch and os.path.exists(archive_path):
                os.remove(archive_path)
            raise ManifestValidationException(
                f"SHA-256 mismatch for pack '{pack_id}': "
                f"expected {expected_sha256}, got {actual_sha}",
                code=ErrorCode.MANIFEST_INVALID,
            )

        if self._public_key_hex and signature_hex:
            verify_ed25519_hex(actual_sha.encode("utf-8"), signature_hex, self._public_key_hex)

        pack_root = os.path.join(self._packs_dir, pack_id)
        staging_dir = os.path.join(pack_root, f".staging-{version}")
        active_dir = os.path.join(pack_root, "current")
        previous_dir = os.path.join(pack_root, "previous")

        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)
        os.makedirs(staging_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(staging_dir)

            if os.path.exists(previous_dir):
                shutil.rmtree(previous_dir, ignore_errors=True)
            if os.path.exists(active_dir):
                os.replace(active_dir, previous_dir)
            os.replace(staging_dir, active_dir)
        except Exception as exc:
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir, ignore_errors=True)
            if not os.path.exists(active_dir) and os.path.exists(previous_dir):
                os.replace(previous_dir, active_dir)
            raise ManifestValidationException(
                f"Atomic install failed and rolled back for '{pack_id}': {exc}",
                code=ErrorCode.RUNTIME_MISSING,
            ) from exc

        record = InstalledPackRecord(
            pack_id=pack_id,
            version=version,
            install_dir=active_dir,
            sha256=actual_sha,
            installed_at=time.time(),
        )
        self._save_record(record)
        activate_runtime_pack(active_dir)
        return record

    def list_installed(self) -> list[InstalledPackRecord]:
        """Return installed active packs and register valid dirs on sys.path."""
        reg_path = os.path.join(self._packs_dir, self.REGISTRY_FILENAME)
        if not os.path.isfile(reg_path):
            return []
        try:
            with open(reg_path, encoding="utf-8") as f:
                raw = json.load(f)
            records = [InstalledPackRecord(**item) for item in raw.values()]
            for rec in records:
                if os.path.isdir(rec.install_dir):
                    activate_runtime_pack(rec.install_dir)
            return records
        except Exception:
            return []

    def rollback_or_uninstall(self, pack_id: str | None = None) -> None:
        """Roll back to previous version if present, or cleanly wipe installed pack."""
        targets = (
            [os.path.join(self._packs_dir, pack_id)]
            if pack_id
            else [
                os.path.join(self._packs_dir, d)
                for d in os.listdir(self._packs_dir)
                if os.path.isdir(os.path.join(self._packs_dir, d))
            ]
        )
        for pack_root in targets:
            if not os.path.isdir(pack_root):
                continue
            active = os.path.join(pack_root, "current")
            previous = os.path.join(pack_root, "previous")
            if pack_id and os.path.isdir(previous):
                if os.path.isdir(active):
                    shutil.rmtree(active, ignore_errors=True)
                os.replace(previous, active)
            else:
                shutil.rmtree(pack_root, ignore_errors=True)
        self._remove_registry_entries(pack_id)

    def _save_record(self, record: InstalledPackRecord) -> None:
        reg_path = os.path.join(self._packs_dir, self.REGISTRY_FILENAME)
        data: dict[str, Any] = {}
        if os.path.isfile(reg_path):
            try:
                with open(reg_path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[record.pack_id] = asdict(record)
        tmp = f"{reg_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, reg_path)

    def _remove_registry_entries(self, pack_id: str | None) -> None:
        reg_path = os.path.join(self._packs_dir, self.REGISTRY_FILENAME)
        if not os.path.isfile(reg_path):
            return
        if pack_id is None:
            os.remove(reg_path)
            return
        try:
            with open(reg_path, encoding="utf-8") as f:
                data = json.load(f)
            data.pop(pack_id, None)
            tmp = f"{reg_path}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, reg_path)
        except Exception:
            pass
