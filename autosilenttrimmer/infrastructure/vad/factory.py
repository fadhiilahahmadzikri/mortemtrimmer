"""Factory for instantiating VAD engines."""

from __future__ import annotations

from autosilenttrimmer.core.config import VADConfig
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.infrastructure.vad.energy import EnergyBasedVAD
from autosilenttrimmer.infrastructure.vad.silero import SileroBasedVAD
from autosilenttrimmer.infrastructure.vad.whisper import WhisperBasedVAD


class VADFactory:
    """Factory creating VAD strategies."""

    @staticmethod
    def create_vad(
        method_name: str, config: VADConfig | None = None
    ) -> IVoiceActivityDetector | None:
        normalized_name = method_name.lower().strip()
        if normalized_name == "energy":
            return EnergyBasedVAD(config=config)
        elif normalized_name == "whisper":
            return WhisperBasedVAD(config=config)
        elif normalized_name == "silero":
            return SileroBasedVAD(config=config)
        return None
