# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Spectral gating noise reduction using noisereduce."""

from __future__ import annotations

import logging

import soundfile as sf

from autosilenttrimmer.core.config import NoiseReductionConfig
from autosilenttrimmer.core.exceptions import DependencyMissingException
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy

logger = logging.getLogger(__name__)


class SpectralGatingStrategy(INoiseReductionStrategy):
    """Classical spectral gating noise reduction."""

    def __init__(self, config: NoiseReductionConfig | None = None) -> None:
        self._config = config or NoiseReductionConfig()

    def process(self, input_path: str, output_path: str) -> None:
        try:
            import noisereduce as nr
        except ImportError as e:
            raise DependencyMissingException(
                "Missing dependency 'noisereduce' for Spectral Gating."
            ) from e

        logger.info("Applying Spectral Gating noise reduction...")
        audio_data, sample_rate = sf.read(input_path, dtype="float32")

        prop_decrease = self._config.spectral_prop_decrease

        if len(audio_data.shape) > 1:
            audio_data = audio_data.T
            reduced_audio = nr.reduce_noise(
                y=audio_data, sr=sample_rate, prop_decrease=prop_decrease
            )
            reduced_audio = reduced_audio.T
        else:
            reduced_audio = nr.reduce_noise(
                y=audio_data, sr=sample_rate, prop_decrease=prop_decrease
            )

        sf.write(output_path, reduced_audio, sample_rate)
