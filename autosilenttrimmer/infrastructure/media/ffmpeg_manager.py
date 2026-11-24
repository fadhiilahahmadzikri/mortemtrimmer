"""FFmpeg media manager for audio extraction, multiplexing, and precision splicing."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile

from autosilenttrimmer.core.constants import (
    AUDIO_CODEC_AAC,
    AUDIO_CODEC_COPY,
    AUDIO_CODEC_PCM_S16LE,
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_AUDIO_CHANNELS_MONO,
    DEFAULT_SAMPLE_RATE_DEEPFILTER,
    DEFAULT_X264_BF,
    DEFAULT_X264_CRF,
    DEFAULT_X264_PRESET,
    TEMP_SCRIPT_SUFFIX,
    VIDEO_CODEC_COPY,
    VIDEO_CODEC_LIBX264,
    VIDEO_EXTENSIONS,
)
from autosilenttrimmer.core.exceptions import FFmpegExecutionException
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.entities.segment import MediaSegment

logger = logging.getLogger(__name__)


class FFmpegMediaManager(IMediaManager):
    """Media manager implementation driven by FFmpeg CLI subprocess."""

    def __init__(self, ffmpeg_path: str) -> None:
        self._ffmpeg_path = ffmpeg_path
        if not os.path.exists(self._ffmpeg_path):
            raise FFmpegExecutionException(
                f"FFmpeg executable not found at specified path: {self._ffmpeg_path}"
            )
        self._verify_ffmpeg_active()

    def _get_clean_env(self) -> dict[str, str]:
        env = os.environ.copy()
        ffmpeg_dir = os.path.dirname(self._ffmpeg_path)
        clean_path = [p for p in env.get("PATH", "").split(os.pathsep) if "venv" not in p.lower()]
        env["PATH"] = os.pathsep.join([ffmpeg_dir, *clean_path])
        return env

    def _verify_ffmpeg_active(self) -> None:
        logger.info("Validating FFmpeg executable integrity...")
        try:
            subprocess.run(
                [self._ffmpeg_path, "-version"],
                check=True,
                capture_output=True,
                text=True,
                env=self._get_clean_env(),
            )
        except subprocess.CalledProcessError as e:
            raise FFmpegExecutionException(
                f"FFmpeg returned error code during integrity check:\n{e.stderr}"
            ) from e
        except OSError as e:
            raise FFmpegExecutionException(
                f"Failed to execute FFmpeg at {self._ffmpeg_path}: {e}"
            ) from e

    def extract_audio(self, source_media_path: str, destination_audio_path: str) -> None:
        logger.info(
            "Extracting audio stream (%d Hz mono PCM)...",
            DEFAULT_SAMPLE_RATE_DEEPFILTER,
        )
        command = [
            self._ffmpeg_path,
            "-y",
            "-i",
            source_media_path,
            "-vn",
            "-acodec",
            AUDIO_CODEC_PCM_S16LE,
            "-ar",
            str(DEFAULT_SAMPLE_RATE_DEEPFILTER),
            "-ac",
            str(DEFAULT_AUDIO_CHANNELS_MONO),
            destination_audio_path,
        ]
        self._run_ffmpeg(command)

    def merge_audio(self, video_path: str, clean_audio_path: str, output_path: str) -> None:
        logger.info("Multiplexing clean audio with source video stream...")
        command = [
            self._ffmpeg_path,
            "-y",
            "-i",
            video_path,
            "-i",
            clean_audio_path,
            "-c:v",
            VIDEO_CODEC_COPY,
            "-c:a",
            AUDIO_CODEC_AAC,
            "-b:a",
            DEFAULT_AUDIO_BITRATE,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            output_path,
        ]
        self._run_ffmpeg(command)

    def export_audio(self, clean_audio_path: str, output_path: str) -> None:
        logger.info("Exporting audio stream...")
        out_ext = os.path.splitext(output_path)[1].lower()
        codec = AUDIO_CODEC_COPY if out_ext == ".wav" else AUDIO_CODEC_AAC
        command = [
            self._ffmpeg_path,
            "-y",
            "-i",
            clean_audio_path,
            "-c:a",
            codec,
        ]
        if codec == AUDIO_CODEC_AAC:
            command.extend(["-b:a", DEFAULT_AUDIO_BITRATE])
        command.append(output_path)
        self._run_ffmpeg(command)

    def slice_and_concat(
        self,
        media_path: str,
        segments: list[MediaSegment],
        output_path: str,
    ) -> None:
        if not segments:
            shutil.copy(media_path, output_path)
            return

        _, ext = os.path.splitext(media_path)
        is_video = ext.lower() in VIDEO_EXTENSIONS
        total_keep = sum(s.duration for s in segments)
        count = len(segments)

        logger.info("Splicing %d segments | Retained duration: %.2fs", count, total_keep)

        fc_path = None
        try:
            filter_parts: list[str] = []

            if count == 1:
                start, end = segments[0].start, segments[0].end
                if is_video:
                    filter_parts.append(
                        f"[0:v]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[vout];"
                    )
                    filter_parts.append(
                        f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[aout]"
                    )
                    map_args = ["-map", "[vout]", "-map", "[aout]"]
                    codec_args = [
                        "-c:v",
                        VIDEO_CODEC_LIBX264,
                        "-bf",
                        DEFAULT_X264_BF,
                        "-crf",
                        DEFAULT_X264_CRF,
                        "-preset",
                        DEFAULT_X264_PRESET,
                        "-c:a",
                        AUDIO_CODEC_AAC,
                        "-b:a",
                        DEFAULT_AUDIO_BITRATE,
                    ]
                else:
                    filter_parts.append(
                        f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[aout]"
                    )
                    map_args = ["-map", "[aout]"]
                    codec_args = ["-c:a", AUDIO_CODEC_PCM_S16LE]
            else:
                if is_video:
                    split_v = "".join(f"[v_s{i}]" for i in range(count))
                    split_a = "".join(f"[a_s{i}]" for i in range(count))
                    filter_parts.append(f"[0:v]split={count}{split_v};")
                    filter_parts.append(f"[0:a]asplit={count}{split_a};")

                    for i, seg in enumerate(segments):
                        filter_parts.append(
                            f"[v_s{i}]trim=start={seg.start:.6f}:end={seg.end:.6f},"
                            f"setpts=PTS-STARTPTS[v{i}];"
                        )
                        filter_parts.append(
                            f"[a_s{i}]atrim=start={seg.start:.6f}:end={seg.end:.6f},"
                            f"asetpts=PTS-STARTPTS[a{i}];"
                        )

                    v_inputs = "".join(f"[v{i}]" for i in range(count))
                    a_inputs = "".join(f"[a{i}]" for i in range(count))

                    filter_parts.append(f"{v_inputs}concat=n={count}:v=1:a=0[vout];")
                    filter_parts.append(f"{a_inputs}concat=n={count}:v=0:a=1[aout]")

                    map_args = ["-map", "[vout]", "-map", "[aout]"]
                    codec_args = [
                        "-c:v",
                        VIDEO_CODEC_LIBX264,
                        "-bf",
                        DEFAULT_X264_BF,
                        "-crf",
                        DEFAULT_X264_CRF,
                        "-preset",
                        DEFAULT_X264_PRESET,
                        "-c:a",
                        AUDIO_CODEC_AAC,
                        "-b:a",
                        DEFAULT_AUDIO_BITRATE,
                    ]
                else:
                    split_a = "".join(f"[a_s{i}]" for i in range(count))
                    filter_parts.append(f"[0:a]asplit={count}{split_a};")

                    for i, seg in enumerate(segments):
                        filter_parts.append(
                            f"[a_s{i}]atrim=start={seg.start:.6f}:end={seg.end:.6f},"
                            f"asetpts=PTS-STARTPTS[a{i}];"
                        )

                    a_inputs = "".join(f"[a{i}]" for i in range(count))
                    filter_parts.append(f"{a_inputs}concat=n={count}:v=0:a=1[aout]")

                    map_args = ["-map", "[aout]"]
                    codec_args = ["-c:a", AUDIO_CODEC_PCM_S16LE]

            filter_complex = "".join(filter_parts)

            fd_fc, fc_path = tempfile.mkstemp(suffix=TEMP_SCRIPT_SUFFIX)
            os.close(fd_fc)
            with open(fc_path, "w", encoding="utf-8") as f:
                f.write(filter_complex)

            logger.info("Executing filter complex concat with %d segments...", count)
            command = [
                self._ffmpeg_path,
                "-y",
                "-i",
                media_path,
                "-filter_complex_script",
                fc_path,
                *map_args,
                *codec_args,
                output_path,
            ]
            self._run_ffmpeg(command)

        finally:
            if fc_path and os.path.exists(fc_path):
                os.remove(fc_path)

    def _run_ffmpeg(self, command: list[str]) -> None:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=self._get_clean_env(),
            )
        except subprocess.CalledProcessError as e:
            raise FFmpegExecutionException(f"FFmpeg execution failed:\n{e.stderr}") from e
        except OSError as e:
            raise FFmpegExecutionException(
                f"OS failed to invoke FFmpeg ({self._ffmpeg_path}): {e}"
            ) from e
