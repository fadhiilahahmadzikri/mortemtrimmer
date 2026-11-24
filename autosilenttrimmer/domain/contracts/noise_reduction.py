# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Noise reduction strategy contract."""

from abc import ABC, abstractmethod


class INoiseReductionStrategy(ABC):
    """Abstract interface for audio noise reduction algorithms."""

    @abstractmethod
    def process(self, input_path: str, output_path: str) -> None:
        """Process input audio file and output denoised audio."""
        pass
