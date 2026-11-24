"""Processing command model."""

from __future__ import annotations

from dataclasses import dataclass

from autosilenttrimmer.core.constants import (
    DEFAULT_FFMPEG_EXECUTABLE,
    DEFAULT_MIN_SILENCE_GAP_SEC,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_PAD_SEC,
    DEFAULT_VAD_METHOD,
)


@dataclass(frozen=True)
class ProcessMediaCommand:
    """Command encapsulating input parameters for processing media."""

    input_path: str
    output_path: str
    noise_reduction_method: str = DEFAULT_NOISE_REDUCTION_METHOD
    vad_method: str = DEFAULT_VAD_METHOD
    min_silence_gap: float = DEFAULT_MIN_SILENCE_GAP_SEC
    pad: float = DEFAULT_PAD_SEC
    ffmpeg_path: str | None = DEFAULT_FFMPEG_EXECUTABLE
