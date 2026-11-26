# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Processing command and neutral JobRequest models (Doc 01 §6.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autosilenttrimmer.core.constants import (
    DEFAULT_COMPUTE_POLICY,
    DEFAULT_FFMPEG_EXECUTABLE,
    DEFAULT_MIN_SILENCE_GAP_SEC,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_ON_CONFLICT,
    DEFAULT_OUTPUT_LOCATION,
    DEFAULT_OUTPUT_NAMING_TEMPLATE,
    DEFAULT_PAD_SEC,
    DEFAULT_TRIM_STRATEGY,
    DEFAULT_VAD_METHOD,
)


@dataclass(frozen=True)
class ProcessMediaCommand:
    """Command encapsulating input parameters for single-file processing."""

    input_path: str
    output_path: str | None = None
    output_dir: str | None = None
    noise_reduction_method: str = DEFAULT_NOISE_REDUCTION_METHOD
    vad_method: str = DEFAULT_VAD_METHOD
    min_silence_gap: float = DEFAULT_MIN_SILENCE_GAP_SEC
    pad: float = DEFAULT_PAD_SEC
    ffmpeg_path: str | None = DEFAULT_FFMPEG_EXECUTABLE
    strategy: str = DEFAULT_TRIM_STRATEGY
    compute_policy: str = DEFAULT_COMPUTE_POLICY
    max_workers: int | None = None
    on_conflict: str = DEFAULT_ON_CONFLICT
    output_location: str = DEFAULT_OUTPUT_LOCATION
    output_naming_template: str = DEFAULT_OUTPUT_NAMING_TEMPLATE
    strategy_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DestinationPromptRequest:
    """Context passed to interactive destination selector when a target drive lacks space."""

    source_path: str
    target_path: str
    free_bytes: int
    required_bytes: int
