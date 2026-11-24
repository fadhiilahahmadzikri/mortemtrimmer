"""Media container, stream, keyframe, VFR, rotation, and HDR prober powered by PyAV."""

from __future__ import annotations

import contextlib
import os

import av

from autosilenttrimmer.core.constants import SUPPORTED_MEDIA_EXTENSIONS, VIDEO_EXTENSIONS
from autosilenttrimmer.core.exceptions import (
    FormatMismatchException,
    MediaFileNotFoundException,
)
from autosilenttrimmer.domain.contracts.media_prober import IMediaProber
from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo, StreamSummary


class PyAVMediaProber(IMediaProber):
    """Cross-platform libavformat/libavcodec prober avoiding external ffprobe subprocesses."""

    def probe(self, media_path: str) -> MediaProbeInfo:
        """Inspect streams, duration, keyframes, rotation, HDR, and VFR flags."""
        if not os.path.isfile(media_path):
            raise MediaFileNotFoundException(f"Input file does not exist: {media_path}")

        _, ext = os.path.splitext(media_path)
        ext_lower = ext.lower()
        if ext_lower not in SUPPORTED_MEDIA_EXTENSIONS:
            raise FormatMismatchException(f"Unsupported media container extension: {ext_lower}")

        file_size = os.path.getsize(media_path)

        try:
            with av.open(media_path) as container:
                duration_sec = (
                    float(container.duration / av.time_base)
                    if container.duration is not None
                    else 0.0
                )
                v_streams: list[StreamSummary] = []
                a_streams: list[StreamSummary] = []
                s_streams: list[StreamSummary] = []
                is_vfr = False
                is_hdr = False
                rotation = 0

                for stream in container.streams:
                    summary = StreamSummary(
                        index=stream.index,
                        media_type=stream.type,
                        codec_name=stream.codec_context.name if stream.codec_context else "unknown",
                        sample_rate=getattr(stream.codec_context, "sample_rate", None),
                        channels=getattr(stream.codec_context, "channels", None),
                        width=getattr(stream.codec_context, "width", None),
                        height=getattr(stream.codec_context, "height", None),
                        bit_rate=getattr(stream.codec_context, "bit_rate", None),
                    )
                    if stream.type == "video":
                        v_streams.append(summary)
                        avg_fps = float(stream.average_rate or 0)
                        base_fps = float(stream.guessed_rate or 0)
                        if avg_fps > 0 and base_fps > 0 and abs(avg_fps - base_fps) > 1.0:
                            is_vfr = True
                        trc = str(getattr(stream.codec_context, "color_trc", "") or "")
                        if any(tag in trc.lower() for tag in ("smpte2084", "arib-std-b67", "pq")):
                            is_hdr = True
                        if hasattr(stream, "metadata") and "rotate" in stream.metadata:
                            with contextlib.suppress(ValueError):
                                rotation = int(stream.metadata["rotate"])
                    elif stream.type == "audio":
                        a_streams.append(summary)
                    elif stream.type == "subtitle":
                        s_streams.append(summary)

                keyframes = (
                    self._extract_keyframes(container, container.streams.video[0])
                    if v_streams
                    else []
                )

                if duration_sec <= 0.0 and a_streams:
                    # Fallback compute duration from audio stream metadata
                    aud = container.streams.audio[0]
                    if aud.duration and aud.time_base:
                        duration_sec = float(aud.duration * aud.time_base)

                is_video = len(v_streams) > 0 and ext_lower in VIDEO_EXTENSIONS

                return MediaProbeInfo(
                    path=media_path,
                    container_format=container.format.name,
                    extension=ext_lower,
                    duration_sec=duration_sec,
                    file_size_bytes=file_size,
                    is_video=is_video,
                    is_vfr=is_vfr,
                    rotation_degrees=rotation,
                    is_hdr=is_hdr,
                    video_streams=tuple(v_streams),
                    audio_streams=tuple(a_streams),
                    subtitle_streams=tuple(s_streams),
                    keyframe_timestamps=tuple(sorted(set(keyframes))),
                )
        except av.AVError as exc:
            raise FormatMismatchException(f"Container or codec could not be opened: {exc}") from exc

    @staticmethod
    def _extract_keyframes(container: object, primary_video: object) -> list[float]:
        """Extract keyframe timestamps via O(1) index table when available, else demux packets."""
        tb = getattr(primary_video, "time_base", None)
        if tb is None:
            return []
        time_base = float(tb)
        start_pts = getattr(primary_video, "start_time", None) or 0
        index_entries = getattr(primary_video, "index_entries", None)
        if index_entries:
            indexed = [
                round(max(0.0, float(entry.timestamp - start_pts) * time_base), 6)
                for entry in index_entries
                if entry.is_keyframe
            ]
            if indexed:
                return indexed
        return [
            round(float(packet.pts) * time_base, 6)
            for packet in container.demux(primary_video)  # type: ignore[attr-defined]
            if packet.is_keyframe and packet.pts is not None
        ]
