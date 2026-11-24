"""Visualizer contract for timeline plotting."""

from __future__ import annotations

from abc import ABC, abstractmethod
from autosilenttrimmer.domain.entities.segment import MediaSegment


class IVisualizer(ABC):
    """Abstract interface for generating visual timeline plots."""

    @abstractmethod
    def generate_timeline_plot(
        self,
        segments: list[MediaSegment],
        total_duration: float,
        output_path: str,
    ) -> str:
        """Generate a visual timeline plot of retained vs discarded segments."""
        pass
