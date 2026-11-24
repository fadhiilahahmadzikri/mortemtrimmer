"""Runtime pack, installer artifact, and signed release manifest models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InstallerArtifact:
    """Platform-arch installer metadata exposed for website landing page and updater."""

    platform_tag: str
    url: str | None
    sha256: str = ""
    signature_ed25519: str = ""
    size_bytes: int = 0
    status: str = "planned"  # "available" | "beta" | "planned"
    min_os_version: str = ""


@dataclass(frozen=True)
class RuntimePackArtifact:
    """Individually versioned and hashed downloadable runtime component."""

    pack_id: str  # e.g. "ffmpeg-windows-x86_64", "ai-cpu-windows-x86_64"
    pack_type: str  # "ffmpeg" | "ai-cpu" | "ai-cuda12" | "ai-mps" | "ai-rocm"
    platform_tag: str
    version: str
    url: str
    sha256: str
    signature_ed25519: str = ""
    size_bytes: int = 0
    requires_gpu: bool = False
    vendor: str | None = None


@dataclass(frozen=True)
class ReleaseManifest:
    """Signed platform-agnostic release catalog consumed by RuntimeManager and Landing Page."""

    schema_version: str
    app_version: str
    channel: str
    installers: dict[str, InstallerArtifact] = field(default_factory=dict)
    runtime_packs: dict[str, RuntimePackArtifact] = field(default_factory=dict)
    release_notes_url: str | None = None


@dataclass(frozen=True)
class InstalledPackRecord:
    """Metadata of an installed and verified local runtime pack."""

    pack_id: str
    version: str
    install_dir: str
    sha256: str
    installed_at: float
