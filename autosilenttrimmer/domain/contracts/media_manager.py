"""Media manager contract for audio extraction, multiplexing, chunk encoding, and splicing."""

from __future__ import annotations

from abc import ABC, abstractmethod

from autosilenttrimmer.domain.entities.segment import MediaSegment


class IMediaManager(ABC):
    """Abstract interface for video/audio extraction, muxing, chunking, and concatenation."""

    @abstractmethod
    def extract_audio(self, source_media_path: str, destination_audio_path: str) -> None:
        """Extract a PCM audio stream from a media file."""
        pass

    @abstractmethod
    def merge_audio(self, video_path: str, clean_audio_path: str, output_path: str) -> None:
        """Multiplex clean audio back into the original video container without re-encoding video."""
        pass

    @abstractmethod
    def export_audio(self, clean_audio_path: str, output_path: str) -> None:
        """Export clean audio into the requested audio container."""
        pass

    @abstractmethod
    def slice_and_concat(
        self,
        media_path: str,
        segments: list[MediaSegment],
        output_path: str,
        *,
        video_encoder: str = "libx264",
        copy_mode: bool = False,
    ) -> None:
        """Perform frame-accurate cutting and concatenation of media segments."""
        pass

    @abstractmethod
    def concat_files(self, chunk_paths: list[str], output_path: str, is_video: bool) -> None:
        """Losslessly concatenate already-trimmed homogeneous chunks via concat demuxer."""
        pass
