"""Factory for instantiating noise reduction strategies."""

from __future__ import annotations

from autosilenttrimmer.core.config import NoiseReductionConfig
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy
from autosilenttrimmer.infrastructure.noise_reduction.deepfilter import DeepFilterNetStrategy
from autosilenttrimmer.infrastructure.noise_reduction.spectral import SpectralGatingStrategy


class NoiseReductionFactory:
    """Factory creating noise reduction strategies."""

    @staticmethod
    def create_noise_reduction(
        method_name: str, config: NoiseReductionConfig | None = None
    ) -> INoiseReductionStrategy | None:
        normalized_name = method_name.lower().strip()
        if normalized_name == "spectral":
            return SpectralGatingStrategy(config=config)
        elif normalized_name == "deepfilter":
            return DeepFilterNetStrategy(config=config)
        return None
