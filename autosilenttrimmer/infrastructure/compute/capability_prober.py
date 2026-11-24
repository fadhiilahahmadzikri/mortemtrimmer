"""Cross-platform host capability prober with driver-fingerprint caching."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import asdict
from typing import Any

import psutil
from autosilenttrimmer.core.constants import HW_ENCODER_CANDIDATES
from autosilenttrimmer.domain.contracts.compute import ICapabilityProber
from autosilenttrimmer.domain.contracts.ffmpeg_locator import IFFmpegLocator
from autosilenttrimmer.domain.models.compute import (
    ComputeCapabilities,
    GPUAdapterInfo,
    PlatformSpec,
)

logger = logging.getLogger(__name__)


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class CrossPlatformCapabilityProber(ICapabilityProber):
    """Probes CPU, RAM, multi-vendor GPUs, and live FFmpeg hardware encoders."""

    CACHE_TTL_SEC: float = 86400.0

    def __init__(self, ffmpeg_locator: IFFmpegLocator, cache_file: str | None = None) -> None:
        self._ffmpeg_locator = ffmpeg_locator
        self._cache_file = cache_file

    def probe(self, force_refresh: bool = False) -> ComputeCapabilities:
        """Probe hardware capabilities, reusing valid cache matching current driver fingerprint."""
        platform_spec = PlatformSpec.current()
        adapters = self._detect_gpu_adapters(platform_spec)
        driver_fp = self._build_driver_fingerprint(adapters)

        if not force_refresh and self._cache_file:
            cached = self._load_cache(driver_fp, platform_spec)
            if cached is not None:
                return cached

        mem = psutil.virtual_memory()
        logical_cores = psutil.cpu_count(logical=True) or 2
        physical_cores = psutil.cpu_count(logical=False) or max(1, logical_cores // 2)
        ai_device = self._detect_ai_device()
        hw_encoders = self._probe_ffmpeg_encoders()

        caps = ComputeCapabilities(
            platform_spec=platform_spec,
            logical_cores=logical_cores,
            physical_cores=physical_cores,
            total_ram_bytes=int(mem.total),
            available_ram_bytes=int(mem.available),
            ai_device=ai_device,
            gpu_adapters=tuple(adapters),
            hw_video_encoders=tuple(hw_encoders),
            driver_fingerprint=driver_fp,
            probe_timestamp=time.time(),
        )

        if self._cache_file:
            self._save_cache(caps)
        return caps

    def _detect_ai_device(self) -> str:
        """Determine PyTorch inference device safely (even if AI runtime is not installed yet)."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def _detect_gpu_adapters(self, platform_spec: PlatformSpec) -> list[GPUAdapterInfo]:
        """Detect vendor-agnostic GPU adapters across Windows, macOS, and Linux."""
        if platform_spec.os_name == "windows":
            return self._detect_windows_gpus()
        if platform_spec.os_name == "darwin":
            return [GPUAdapterInfo(name="Apple Silicon / Metal", vendor="apple", supports_mps=True)]
        return self._detect_linux_gpus()

    def _detect_windows_gpus(self) -> list[GPUAdapterInfo]:
        """Query Windows GPU controllers cleanly via CIM without shell errors."""
        adapters: list[GPUAdapterInfo] = []
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress",
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
                creationflags=_creation_flags(),
            )
            if res.returncode == 0 and res.stdout.strip():
                raw = json.loads(res.stdout)
                items = raw if isinstance(raw, list) else [raw]
                for item in items:
                    name = str(item.get("Name") or "").strip()
                    if not name or "virtual" in name.lower():
                        continue
                    lower = name.lower()
                    vendor = (
                        "nvidia"
                        if "nvidia" in lower
                        else (
                            "amd"
                            if ("amd" in lower or "radeon" in lower)
                            else ("intel" if "intel" in lower else "other")
                        )
                    )
                    adapters.append(
                        GPUAdapterInfo(
                            name=name,
                            vendor=vendor,
                            driver_version=str(item.get("DriverVersion") or "unknown"),
                            vram_bytes=int(item.get("AdapterRAM") or 0),
                            supports_cuda=(vendor == "nvidia"),
                        )
                    )
        except Exception as exc:
            logger.debug("Windows GPU CIM query skipped: %s", exc)
        return adapters

    def _detect_linux_gpus(self) -> list[GPUAdapterInfo]:
        adapters: list[GPUAdapterInfo] = []
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if parts and parts[0]:
                        adapters.append(
                            GPUAdapterInfo(
                                name=parts[0],
                                vendor="nvidia",
                                driver_version=parts[1] if len(parts) > 1 else "unknown",
                                supports_cuda=True,
                            )
                        )
        except OSError:
            pass
        return adapters

    def _probe_ffmpeg_encoders(self) -> list[str]:
        """Dry-run FFmpeg 1-frame encodes to confirm working hardware encoders."""
        try:
            ffmpeg_path = self._ffmpeg_locator.locate()
        except Exception:
            return []

        operational: list[str] = []
        for _tag, codec in HW_ENCODER_CANDIDATES:
            cmd = [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=256x256:r=30:d=0.04",
                "-frames:v",
                "1",
                "-c:v",
                codec,
                "-f",
                "null",
                "-",
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                    creationflags=_creation_flags(),
                )
                if res.returncode == 0:
                    operational.append(codec)
            except Exception:
                continue
        return operational

    @staticmethod
    def _build_driver_fingerprint(adapters: list[GPUAdapterInfo]) -> str:
        if not adapters:
            return "cpu-only"
        return "|".join(f"{a.vendor}:{a.driver_version}" for a in adapters)

    def _load_cache(
        self, expected_fp: str, platform_spec: PlatformSpec
    ) -> ComputeCapabilities | None:
        if not self._cache_file or not os.path.isfile(self._cache_file):
            return None
        try:
            with open(self._cache_file, encoding="utf-8") as f:
                data = json.load(f)
            if (
                data.get("driver_fingerprint") != expected_fp
                or data.get("platform_spec", {}).get("os_name") != platform_spec.os_name
                or (time.time() - float(data.get("probe_timestamp", 0))) > self.CACHE_TTL_SEC
            ):
                return None

            mem = psutil.virtual_memory()
            adapters = tuple(GPUAdapterInfo(**a) for a in data.get("gpu_adapters", []))
            return ComputeCapabilities(
                platform_spec=platform_spec,
                logical_cores=int(data["logical_cores"]),
                physical_cores=int(data["physical_cores"]),
                total_ram_bytes=int(mem.total),
                available_ram_bytes=int(mem.available),
                ai_device=str(data.get("ai_device", "cpu")),
                gpu_adapters=adapters,
                hw_video_encoders=tuple(data.get("hw_video_encoders", [])),
                driver_fingerprint=expected_fp,
                probe_timestamp=float(data["probe_timestamp"]),
            )
        except Exception:
            return None

    def _save_cache(self, caps: ComputeCapabilities) -> None:
        if not self._cache_file:
            return
        try:
            parent = os.path.dirname(os.path.abspath(self._cache_file))
            os.makedirs(parent, exist_ok=True)
            payload: dict[str, Any] = asdict(caps)
            tmp = f"{self._cache_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, self._cache_file)
        except OSError as exc:
            logger.debug("Could not cache compute capabilities: %s", exc)
