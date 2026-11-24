"""Signed update availability checker respecting idle queues (Doc 02 §5.7)."""

from __future__ import annotations

from autosilenttrimmer.core.constants import APP_VERSION
from autosilenttrimmer.domain.contracts.runtime_manager import IRuntimeManager
from autosilenttrimmer.domain.models.compute import PlatformSpec
from autosilenttrimmer.domain.models.runtime_pack import InstallerArtifact
from packaging.version import Version


class ManifestUpdateChecker:
    """Queries signed release manifest for newer installers without interrupting active jobs."""

    def __init__(self, runtime_manager: IRuntimeManager) -> None:
        self._runtime_manager = runtime_manager

    def check_for_update(
        self,
        manifest_url: str,
        channel: str = "stable",
        current_version: str = APP_VERSION,
    ) -> InstallerArtifact | None:
        """Return InstallerArtifact if a newer version exists for current OS/arch."""
        manifest = self._runtime_manager.fetch_manifest(manifest_url, channel=channel)
        if Version(manifest.app_version) <= Version(current_version):
            return None
        tag = PlatformSpec.current().platform_tag
        artifact = manifest.installers.get(tag)
        if artifact and artifact.status == "available" and artifact.url:
            return artifact
        return None
