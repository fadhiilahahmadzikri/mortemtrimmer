"""Compute capability prober, backend selection, and process priority contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from autosilenttrimmer.domain.models.compute import (
    BackendSelection,
    ComputeCapabilities,
    ComputePolicy,
)


class ICapabilityProber(ABC):
    """Probes host CPU, RAM, GPU adapters, and operational FFmpeg hardware encoders."""

    @abstractmethod
    def probe(self, force_refresh: bool = False) -> ComputeCapabilities:
        """Return cached or freshly measured host compute capabilities."""
        pass


class IComputeBackend(ABC):
    """Selects optimal compute backend + encoder policy with clean CPU fallback."""

    @abstractmethod
    def select_backend(
        self,
        policy: ComputePolicy,
        ffmpeg_path: str,
        requested_max_workers: int | None = None,
    ) -> BackendSelection:
        """Select backend adhering to G1/G2/G3 policy or raise NO_COMPUTE_BACKEND."""
        pass

    @abstractmethod
    def fallback_to_cpu(self, reason: str) -> BackendSelection:
        """Produce CPU fallback backend selection on GPU runtime error."""
        pass


class IProcessPriorityController(ABC):
    """Controls OS scheduling priority and battery/power awareness (Doc 01 §7.5)."""

    @abstractmethod
    def apply_background_priority(self) -> None:
        """Lower current process/worker priority so desktop remains responsive."""
        pass

    @abstractmethod
    def is_low_battery(self) -> bool:
        """Return true when running on battery below safe threshold."""
        pass
