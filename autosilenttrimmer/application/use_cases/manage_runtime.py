# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Runtime pack setup, manifest fetch, verification, and rollback use case."""

from __future__ import annotations

import logging

from autosilenttrimmer.domain.contracts.compute import ICapabilityProber
from autosilenttrimmer.domain.contracts.runtime_manager import IRuntimeManager
from autosilenttrimmer.domain.models.compute import PlatformSpec
from autosilenttrimmer.domain.models.runtime_pack import InstalledPackRecord

logger = logging.getLogger(__name__)


class ManageRuntimeUseCase:
    """Executes Doc 02 §5.3 first-run Runtime Pack probing and idempotent installation."""

    def __init__(
        self,
        runtime_manager: IRuntimeManager,
        capability_prober: ICapabilityProber,
    ) -> None:
        self._runtime_manager = runtime_manager
        self._prober = capability_prober

    def install_for_current_host(
        self, manifest_url: str, channel: str = "stable"
    ) -> list[InstalledPackRecord]:
        """Probe hardware, select matching platform/arch/GPU packs, and install atomically."""
        spec = PlatformSpec.current()
        caps = self._prober.probe(force_refresh=True)
        manifest = self._runtime_manager.fetch_manifest(manifest_url, channel=channel)
        packs = self._runtime_manager.select_packs_for_host(manifest, spec, caps)

        if not packs:
            logger.info("No external runtime packs required for %s.", spec.platform_tag)
            return []

        installed: list[InstalledPackRecord] = []
        for pack in packs:
            logger.info(
                "Installing runtime pack '%s' v%s (%d bytes)...",
                pack.pack_id,
                pack.version,
                pack.size_bytes,
            )
            installed.append(self._runtime_manager.install_pack(pack))
        return installed
