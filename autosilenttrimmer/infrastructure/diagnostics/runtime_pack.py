"""Platform architecture, runtime packs, and shell readiness diagnostics."""

from __future__ import annotations

from autosilenttrimmer.core.constants import TIER1_VIDEO_EXTENSIONS
from autosilenttrimmer.domain.contracts.compute import ICapabilityProber
from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.contracts.platform_paths import IPlatformPaths
from autosilenttrimmer.domain.contracts.runtime_manager import IRuntimeManager
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration
from autosilenttrimmer.domain.models.compute import PlatformSpec
from autosilenttrimmer.domain.models.readiness import ReadinessItem, ReadinessStatus


class ProductionReadinessDiagnostic(ISystemDiagnostic):
    """Verifies platform target, hardware encoders, managed packs, storage, and shell menu."""

    def __init__(
        self,
        paths: IPlatformPaths,
        capability_prober: ICapabilityProber,
        runtime_manager: IRuntimeManager,
        shell_integration: IShellIntegration | None = None,
    ) -> None:
        self._paths = paths
        self._prober = capability_prober
        self._runtime_manager = runtime_manager
        self._shell = shell_integration

    @property
    def category_name(self) -> str:
        return "Production Platform & Runtime Readiness"

    def check(self) -> list[ReadinessItem]:
        """Inspect host platform tag, hardware encoders, storage paths, and shell registration."""
        items: list[ReadinessItem] = []
        spec = PlatformSpec.current()

        items.append(
            ReadinessItem(
                component="Target Platform & Arch",
                category=self.category_name,
                status=ReadinessStatus.READY,
                detail=f"{spec.platform_tag} (Agnostic Manifest Target)",
                is_critical=True,
            )
        )

        self._paths.ensure_all_dirs()
        items.append(
            ReadinessItem(
                component="Per-User Storage Paths",
                category=self.category_name,
                status=ReadinessStatus.READY,
                detail=f"Data dir: {self._paths.data_dir}",
                is_critical=True,
            )
        )

        caps = self._prober.probe()
        if caps.hw_video_encoders:
            items.append(
                ReadinessItem(
                    component="Hardware Video Encoders",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"Operational encoders: {', '.join(caps.hw_video_encoders)}",
                    is_critical=False,
                )
            )
        else:
            items.append(
                ReadinessItem(
                    component="Hardware Video Encoders",
                    category=self.category_name,
                    status=ReadinessStatus.WARNING,
                    detail="No hardware encoder active; software libx264 (CPU) will be used (Policy G2).",
                    is_critical=False,
                )
            )

        installed = self._runtime_manager.list_installed()
        pack_summary = (
            ", ".join(f"{p.pack_id}@{p.version}" for p in installed)
            if installed
            else "Embedded environment active (no external runtime packs downloaded)"
        )
        items.append(
            ReadinessItem(
                component="Managed Runtime Packs",
                category=self.category_name,
                status=ReadinessStatus.AVAILABLE,
                detail=pack_summary,
                is_critical=False,
            )
        )

        if self._shell is not None:
            registered = self._shell.is_registered(TIER1_VIDEO_EXTENSIONS)
            items.append(
                ReadinessItem(
                    component="Shell Context Menu",
                    category=self.category_name,
                    status=ReadinessStatus.READY
                    if registered
                    else ReadinessStatus.OPTIONAL_MISSING,
                    detail=(
                        "Registered ('Trim This Video' active in Explorer)"
                        if registered
                        else "Not registered (run --register-shell to enable right-click menu)"
                    ),
                    is_critical=False,
                )
            )

        return items
