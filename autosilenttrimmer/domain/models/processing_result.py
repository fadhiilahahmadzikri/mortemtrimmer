"""Processing result metrics model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingResult:
    """Outcome metrics of media processing pipeline."""

    input_path: str
    output_path: str
    original_duration: float
    final_duration: float
    silence_removed_duration: float
    reduction_percentage: float
    segments_retained_count: int
    manifest_path: str | None = None
    plot_path: str | None = None
