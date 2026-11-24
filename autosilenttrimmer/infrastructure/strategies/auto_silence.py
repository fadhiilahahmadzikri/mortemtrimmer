"""Auto-silence trim strategy delegating voice detection to IVoiceActivityDetector."""

from __future__ import annotations

from typing import Any

from autosilenttrimmer.domain.contracts.trim_strategy import ITrimStrategy
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo


class AutoSilenceTrimStrategy(ITrimStrategy):
    """Retains active speech segments produced by an injected VAD detector."""

    def __init__(self, vad_detector: IVoiceActivityDetector) -> None:
        self._vad = vad_detector

    @property
    def strategy_id(self) -> str:
        return "auto-silence"

    @property
    def requires_frame_accuracy(self) -> bool:
        return True

    def plan_keep_segments(
        self,
        probe_info: MediaProbeInfo,
        audio_path: str | None = None,
        manifest_path: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[MediaSegment]:
        """Execute VAD analysis on extracted or direct audio to build keep segments."""
        target = audio_path or probe_info.path
        segments = self._vad.get_keep_segments(target, manifest_path=manifest_path)
        if not segments and probe_info.duration_sec > 0.0:
            return []
        return segments
