"""Compute backend, platform architecture, and capability domain models."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from enum import StrEnum


class ComputePolicy(StrEnum):
    """GPU vs CPU fallback policies defined in Doc 01 §8."""

    G1_HARD_GATE = "g1_hard_gate"
    G2_GPU_PREFERRED = "g2_gpu_preferred"
    G3_CPU_ONLY = "g3_cpu_only"


@dataclass(frozen=True)
class PlatformSpec:
    """Normalized host OS and CPU architecture tuple for platform-agnostic distribution."""

    os_name: str  # "windows" | "darwin" | "linux"
    arch: str  # "x86_64" | "arm64"

    @property
    def platform_tag(self) -> str:
        """Return canonical platform-arch key such as 'windows-x86_64'."""
        return f"{self.os_name}-{self.arch}"

    @classmethod
    def current(cls) -> PlatformSpec:
        """Detect and normalize the current runtime platform and architecture."""
        raw_os = platform.system().lower()
        os_map = {"windows": "windows", "darwin": "darwin", "linux": "linux"}
        norm_os = os_map.get(raw_os, raw_os)

        raw_arch = platform.machine().lower()
        if raw_arch in {"amd64", "x86_64", "x64"}:
            norm_arch = "x86_64"
        elif raw_arch in {"arm64", "aarch64"}:
            norm_arch = "arm64"
        else:
            norm_arch = raw_arch

        return cls(os_name=norm_os, arch=norm_arch)


@dataclass(frozen=True)
class GPUAdapterInfo:
    """Detected hardware GPU adapter metadata."""

    name: str
    vendor: str
    driver_version: str = "unknown"
    vram_bytes: int = 0
    supports_cuda: bool = False
    supports_mps: bool = False
    supports_rocm: bool = False


@dataclass(frozen=True)
class ComputeCapabilities:
    """Cached host compute, memory, disk, and encoder capability snapshot."""

    platform_spec: PlatformSpec
    logical_cores: int
    physical_cores: int
    total_ram_bytes: int
    available_ram_bytes: int
    ai_device: str  # "cuda" | "mps" | "cpu"
    gpu_adapters: tuple[GPUAdapterInfo, ...] = field(default_factory=tuple)
    hw_video_encoders: tuple[str, ...] = field(default_factory=tuple)
    driver_fingerprint: str = "cpu"
    probe_timestamp: float = 0.0

    @property
    def has_hw_encoder(self) -> bool:
        """Return true if at least one hardware H.264 encoder is operational."""
        return len(self.hw_video_encoders) > 0

    @property
    def has_gpu_ai(self) -> bool:
        """Return true if GPU-accelerated PyTorch inference is available."""
        return self.ai_device in {"cuda", "mps"}


@dataclass(frozen=True)
class BackendSelection:
    """Resolved backend selection bound to a job or worker execution."""

    backend_id: str  # e.g. "gpu-nvenc", "gpu-qsv", "cpu"
    ai_device: str  # "cuda" | "mps" | "cpu"
    video_encoder: str  # e.g. "h264_nvenc", "h264_qsv", "libx264"
    max_concurrency: int
    is_gpu: bool
    reason: str
