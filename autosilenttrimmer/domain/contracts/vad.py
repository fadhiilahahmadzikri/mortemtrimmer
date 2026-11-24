"""Voice Activity Detector contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from autosilenttrimmer.domain.entities.segment import MediaSegment


class IVoiceActivityDetector(ABC):
    """Abstract interface for voice activity detection engines."""

    @abstractmethod
    def get_keep_segments(
        self, audio_path: str, manifest_path: str | None = None
    ) -> list[MediaSegment]:
        """Detect speech segments and return segments to retain."""
        pass
