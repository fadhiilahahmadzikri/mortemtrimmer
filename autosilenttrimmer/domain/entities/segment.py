"""MediaSegment value object representing an audio/video time slice."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaSegment:
    """Immutable time segment with start and end in seconds."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"Start time cannot be negative: {self.start}")
        if self.end < self.start:
            raise ValueError(
                f"End time ({self.end}) cannot be less than start time ({self.start})"
            )

    @property
    def duration(self) -> float:
        """Calculate slice duration in seconds."""
        return self.end - self.start

    @classmethod
    def merge_overlapping(
        cls, segments: list["MediaSegment"], min_gap: float = 0.0
    ) -> list["MediaSegment"]:
        """Merge overlapping segments or segments separated by less than min_gap seconds."""
        if not segments:
            return []

        sorted_segments = sorted(segments, key=lambda s: s.start)
        merged: list[MediaSegment] = [sorted_segments[0]]

        for current in sorted_segments[1:]:
            prev = merged[-1]
            if current.start - prev.end < min_gap:
                merged[-1] = MediaSegment(
                    start=prev.start,
                    end=max(prev.end, current.end),
                )
            else:
                merged.append(current)

        return merged
