"""Process media use case: backward-compatible single-shot orchestration facade."""

from __future__ import annotations

import logging
import os

from autosilenttrimmer.application.use_cases.job_orchestrator import JobOrchestrator
from autosilenttrimmer.core.config import MediaProcessingConfig
from autosilenttrimmer.domain.contracts.compute import ICapabilityProber, IComputeBackend
from autosilenttrimmer.domain.contracts.event_bus import IEventBus
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.media_prober import IMediaProber
from autosilenttrimmer.domain.contracts.media_verifier import IMediaVerifier
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.contracts.visualizer import IVisualizer
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo
from autosilenttrimmer.domain.models.processing_command import ProcessMediaCommand
from autosilenttrimmer.domain.models.processing_result import ProcessingResult
from autosilenttrimmer.infrastructure.compute.backend_selector import PolicyComputeBackend
from autosilenttrimmer.infrastructure.compute.capability_prober import (
    CrossPlatformCapabilityProber,
)
from autosilenttrimmer.infrastructure.events.in_memory_bus import InMemoryEventBus
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.pyav_prober import PyAVMediaProber
from autosilenttrimmer.infrastructure.media.pyav_verifier import PyAVMediaVerifier
from autosilenttrimmer.infrastructure.strategies.auto_silence import AutoSilenceTrimStrategy

logger = logging.getLogger(__name__)


class _PassThroughStrategy(AutoSilenceTrimStrategy):
    """Retains entire media stream cleanly when VAD strategy is disabled (--vad none)."""

    def __init__(self) -> None:
        pass

    @property
    def strategy_id(self) -> str:
        return "passthrough"

    @property
    def requires_frame_accuracy(self) -> bool:
        return False

    def plan_keep_segments(
        self,
        probe_info: MediaProbeInfo,
        audio_path: str | None = None,
        manifest_path: str | None = None,
        params: dict | None = None,
    ) -> list[MediaSegment]:
        if probe_info.duration_sec <= 0.0:
            return []
        return [MediaSegment(start=0.0, end=probe_info.duration_sec)]


class ProcessMediaUseCase:
    """Use case preserving legacy CLI signature while routing through JobOrchestrator."""

    def __init__(
        self,
        media_manager: IMediaManager,
        vad_strategy: IVoiceActivityDetector | None = None,
        noise_reduction_strategy: INoiseReductionStrategy | None = None,
        visualizer: IVisualizer | None = None,
        *,
        media_prober: IMediaProber | None = None,
        media_verifier: IMediaVerifier | None = None,
        capability_prober: ICapabilityProber | None = None,
        compute_backend: IComputeBackend | None = None,
        event_bus: IEventBus | None = None,
        config: MediaProcessingConfig | None = None,
    ) -> None:
        self._media_manager = media_manager
        self._vad_strategy = vad_strategy
        self._noise_reduction_strategy = noise_reduction_strategy
        self._visualizer = visualizer

        locator = ManagedFFmpegLocator()
        cap_prober = capability_prober or CrossPlatformCapabilityProber(locator)
        backend = compute_backend or PolicyComputeBackend(cap_prober)
        trim_strategy = (
            AutoSilenceTrimStrategy(vad_strategy)
            if vad_strategy is not None
            else _PassThroughStrategy()
        )
        cfg = config or MediaProcessingConfig()

        self._orchestrator = JobOrchestrator(
            media_manager=media_manager,
            media_prober=media_prober or PyAVMediaProber(),
            media_verifier=media_verifier or PyAVMediaVerifier(),
            trim_strategy=trim_strategy,
            capability_prober=cap_prober,
            compute_backend=backend,
            event_bus=event_bus or InMemoryEventBus(),
            config=cfg,
            noise_reduction=noise_reduction_strategy,
            visualizer=visualizer,
        )

    def execute(
        self,
        input_path: str,
        output_path: str | None = None,
        command: ProcessMediaCommand | None = None,
    ) -> ProcessingResult:
        """Execute end-to-end processing pipeline with probing, planning, and verification."""
        if command is not None:
            return self._orchestrator.execute_job(command)
        cmd = ProcessMediaCommand(
            input_path=os.path.abspath(input_path),
            output_path=os.path.abspath(output_path) if output_path else None,
        )
        return self._orchestrator.execute_job(cmd)
