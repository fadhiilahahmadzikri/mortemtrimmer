# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Domain contracts and interfaces (abstract base classes)."""

from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.contracts.ffmpeg_locator import IFFmpegLocator
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.contracts.visualizer import IVisualizer

__all__ = [
    "IFFmpegLocator",
    "IMediaManager",
    "INoiseReductionStrategy",
    "ISystemDiagnostic",
    "IVisualizer",
    "IVoiceActivityDetector",
]
