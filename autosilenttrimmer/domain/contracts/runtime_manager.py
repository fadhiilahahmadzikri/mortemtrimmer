# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Managed Runtime Pack downloader, verifier, installer, and rollback contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from autosilenttrimmer.domain.models.compute import ComputeCapabilities, PlatformSpec
from autosilenttrimmer.domain.models.runtime_pack import (
    InstalledPackRecord,
    ReleaseManifest,
    RuntimePackArtifact,
)


class IRuntimeManager(ABC):
    """Port managing platform-agnostic signed Runtime Pack lifecycle."""

    @abstractmethod
    def fetch_manifest(self, manifest_url: str, channel: str = "stable") -> ReleaseManifest:
        """Download and cryptographically validate signed release manifest."""
        pass

    @abstractmethod
    def select_packs_for_host(
        self,
        manifest: ReleaseManifest,
        platform_spec: PlatformSpec,
        capabilities: ComputeCapabilities,
    ) -> list[RuntimePackArtifact]:
        """Select optimal Runtime Pack variants for current OS, arch, and GPU capabilities."""
        pass

    @abstractmethod
    def install_pack(self, artifact: RuntimePackArtifact) -> InstalledPackRecord:
        """Download (resumable), verify SHA-256/sig, extract atomically, and register pack."""
        pass

    @abstractmethod
    def install_local_pack(self, archive_path: str, expected_sha256: str) -> InstalledPackRecord:
        """Offline installation path for bundled archives."""
        pass

    @abstractmethod
    def list_installed(self) -> list[InstalledPackRecord]:
        """List currently active installed runtime packs."""
        pass

    @abstractmethod
    def rollback_or_uninstall(self, pack_id: str | None = None) -> None:
        """Roll back to previous version or cleanly wipe managed runtime pack."""
        pass
