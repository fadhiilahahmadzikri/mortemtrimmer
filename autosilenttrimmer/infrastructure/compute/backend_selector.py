"""Policy-driven compute backend selector (G1 / G2 / G3)."""

from __future__ import annotations

from autosilenttrimmer.core.constants import (
    DEFAULT_GPU_MAX_SESSIONS,
    DEFAULT_RESERVED_CPU_CORES,
    HW_ENCODER_CANDIDATES,
    VIDEO_CODEC_LIBX264,
)
from autosilenttrimmer.core.exceptions import ComputeBackendException, ErrorCode
from autosilenttrimmer.domain.contracts.compute import ICapabilityProber, IComputeBackend
from autosilenttrimmer.domain.models.compute import (
    BackendSelection,
    ComputeCapabilities,
    ComputePolicy,
)


class PolicyComputeBackend(IComputeBackend):
    """Selects optimal GPU/CPU backend adhering to G1, G2, or G3 compute policies."""

    def __init__(self, prober: ICapabilityProber) -> None:
        self._prober = prober
        self._last_capabilities: ComputeCapabilities | None = None

    def select_backend(
        self,
        policy: ComputePolicy,
        ffmpeg_path: str,
        requested_max_workers: int | None = None,
    ) -> BackendSelection:
        """Select compute backend cleanly without hardcoding single GPU vendor."""
        caps = self._prober.probe()
        self._last_capabilities = caps
        cpu_concurrency = max(1, caps.logical_cores - DEFAULT_RESERVED_CPU_CORES)
        if requested_max_workers and requested_max_workers > 0:
            cpu_concurrency = min(cpu_concurrency, requested_max_workers)

        if policy == ComputePolicy.G3_CPU_ONLY:
            return BackendSelection(
                backend_id="cpu",
                ai_device="cpu",
                video_encoder=VIDEO_CODEC_LIBX264,
                max_concurrency=cpu_concurrency,
                is_gpu=False,
                reason="CPU-only compute policy configured.",
            )

        selected_encoder = self._pick_hw_encoder(caps)
        has_gpu_capability = (selected_encoder is not None) or caps.has_gpu_ai

        if policy == ComputePolicy.G1_HARD_GATE and not has_gpu_capability:
            raise ComputeBackendException(
                "No supported hardware GPU encoder or AI accelerator available under Policy G1.",
                code=ErrorCode.NO_COMPUTE_BACKEND,
            )

        if has_gpu_capability:
            encoder = selected_encoder or VIDEO_CODEC_LIBX264
            max_conc = DEFAULT_GPU_MAX_SESSIONS if selected_encoder is not None else cpu_concurrency
            if requested_max_workers and requested_max_workers > 0:
                max_conc = min(max_conc, requested_max_workers)
            tag = self._encoder_label(encoder)
            return BackendSelection(
                backend_id=f"gpu-{tag}" if selected_encoder else f"gpu-{caps.ai_device}",
                ai_device=caps.ai_device,
                video_encoder=encoder,
                max_concurrency=max(1, max_conc),
                is_gpu=True,
                reason=f"Hardware backend ready (encoder={encoder}, ai={caps.ai_device}).",
            )

        return BackendSelection(
            backend_id="cpu",
            ai_device="cpu",
            video_encoder=VIDEO_CODEC_LIBX264,
            max_concurrency=cpu_concurrency,
            is_gpu=False,
            reason="No operational GPU hardware encoder found; running on CPU.",
        )

    def fallback_to_cpu(self, reason: str) -> BackendSelection:
        """Return safe CPU backend selection on GPU runtime error (Doc 01 §7.8)."""
        cores = self._last_capabilities.logical_cores if self._last_capabilities else 4
        return BackendSelection(
            backend_id="cpu",
            ai_device="cpu",
            video_encoder=VIDEO_CODEC_LIBX264,
            max_concurrency=max(1, cores - DEFAULT_RESERVED_CPU_CORES),
            is_gpu=False,
            reason=f"CPU fallback active: {reason}",
        )

    @staticmethod
    def _pick_hw_encoder(caps: ComputeCapabilities) -> str | None:
        for _tag, codec in HW_ENCODER_CANDIDATES:
            if codec in caps.hw_video_encoders:
                return codec
        return None

    @staticmethod
    def _encoder_label(codec: str) -> str:
        for tag, cand in HW_ENCODER_CANDIDATES:
            if cand == codec:
                return tag
        return "cpu"
