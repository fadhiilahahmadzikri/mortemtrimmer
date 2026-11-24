"""FFmpeg media manager for audio extraction, muxing, chunk encoding, and lossless concat."""

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
from autosilenttrimmer.core.exceptions import FFmpegExecutionException, MergeException
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.entities.segment import MediaSegment

logger = logging.getLogger(__name__)


def _win_no_window_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


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
        logger.debug("Validating FFmpeg executable integrity...")
        try:
            subprocess.run(
                [self._ffmpeg_path, "-version"],
                check=True,
                capture_output=True,
                text=True,
                env=self._get_clean_env(),
                creationflags=_win_no_window_flags(),
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
        *,
        video_encoder: str = VIDEO_CODEC_LIBX264,
        copy_mode: bool = False,
    ) -> None:
        if not segments:
            shutil.copy(media_path, output_path)
            return

        _, ext = os.path.splitext(media_path)
        is_video = ext.lower() in VIDEO_EXTENSIONS

        if copy_mode and is_video and len(segments) == 1:
            start, end = segments[0].start, segments[0].end
            cmd = [
                self._ffmpeg_path,
                "-y",
                "-ss",
                f"{start:.6f}",
                "-to",
                f"{end:.6f}",
                "-i",
                media_path,
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                output_path,
            ]
            self._run_ffmpeg(cmd)
            return

        filter_complex, map_args, codec_args = self._build_filter_graph(
            segments=segments,
            is_video=is_video,
            video_encoder=video_encoder,
        )

        if len(filter_complex) < 6000:
            logger.info(
                "Executing filter complex (%d segments, encoder=%s)...",
                len(segments),
                video_encoder if is_video else AUDIO_CODEC_PCM_S16LE,
            )
            command = [
                self._ffmpeg_path,
                "-y",
                "-i",
                media_path,
                "-filter_complex",
                filter_complex,
                *map_args,
                *codec_args,
                output_path,
            ]
            self._run_ffmpeg(command)
            return

        fd_fc, fc_path = tempfile.mkstemp(suffix=TEMP_SCRIPT_SUFFIX)
        os.close(fd_fc)
        try:
            with open(fc_path, "w", encoding="utf-8") as f:
                f.write(filter_complex)

            logger.info(
                "Executing filter complex file (%d segments, encoder=%s)...",
                len(segments),
                video_encoder if is_video else AUDIO_CODEC_PCM_S16LE,
            )
            command = [
                self._ffmpeg_path,
                "-y",
                "-i",
                media_path,
                "-/filter_complex",
                fc_path,
                *map_args,
                *codec_args,
                output_path,
            ]
            self._run_ffmpeg(command)
        finally:
            if os.path.exists(fc_path):
                os.remove(fc_path)

    def concat_files(self, chunk_paths: list[str], output_path: str, is_video: bool) -> None:
        """Losslessly concatenate chunk artifacts via FFmpeg concat demuxer (Doc 01 §7.6)."""
        if not chunk_paths:
            raise MergeException("No chunk artifacts supplied for concatenation.")
        if len(chunk_paths) == 1:
            shutil.copyfile(chunk_paths[0], output_path)
            return

        fd_list, list_path = tempfile.mkstemp(suffix=TEMP_SCRIPT_SUFFIX)
        os.close(fd_list)
        try:
            with open(list_path, "w", encoding="utf-8") as f:
                for p in chunk_paths:
                    safe = os.path.abspath(p).replace("'", "'\\''")
                    f.write(f"file '{safe}'\n")

            lossless_cmd = [
                self._ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                output_path,
            ]
            try:
                self._run_ffmpeg(lossless_cmd)
                return
            except FFmpegExecutionException as exc:
                logger.warning("Lossless concat failed (%s); falling back to uniform remux.", exc)

            fallback_codec = (
                [
                    "-c:v",
                    VIDEO_CODEC_LIBX264,
                    "-c:a",
                    AUDIO_CODEC_AAC,
                    "-b:a",
                    DEFAULT_AUDIO_BITRATE,
                ]
                if is_video
                else ["-c:a", AUDIO_CODEC_PCM_S16LE]
            )
            fallback_cmd = [
                self._ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                *fallback_codec,
                output_path,
            ]
            try:
                self._run_ffmpeg(fallback_cmd)
            except FFmpegExecutionException as exc:
                raise MergeException(f"Chunk merge failed: {exc}") from exc
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)

    def _build_filter_graph(
        self,
        *,
        segments: list[MediaSegment],
        is_video: bool,
        video_encoder: str,
    ) -> tuple[str, list[str], list[str]]:
        count = len(segments)
        filter_parts: list[str] = []

        if count == 1:
            s, e = segments[0].start, segments[0].end
            if is_video:
                filter_parts.append(
                    f"[0:v]trim=start={s:.6f}:end={e:.6f},setpts=PTS-STARTPTS[vout];"
                )
            filter_parts.append(f"[0:a]atrim=start={s:.6f}:end={e:.6f},asetpts=PTS-STARTPTS[aout]")
        else:
            if is_video:
                split_v = "".join(f"[v_s{i}]" for i in range(count))
                filter_parts.append(f"[0:v]split={count}{split_v};")
            split_a = "".join(f"[a_s{i}]" for i in range(count))
            filter_parts.append(f"[0:a]asplit={count}{split_a};")

            for i, seg in enumerate(segments):
                if is_video:
                    filter_parts.append(
                        f"[v_s{i}]trim=start={seg.start:.6f}:end={seg.end:.6f},"
                        f"setpts=PTS-STARTPTS[v{i}];"
                    )
                filter_parts.append(
                    f"[a_s{i}]atrim=start={seg.start:.6f}:end={seg.end:.6f},"
                    f"asetpts=PTS-STARTPTS[a{i}];"
                )

            if is_video:
                v_inputs = "".join(f"[v{i}]" for i in range(count))
                filter_parts.append(f"{v_inputs}concat=n={count}:v=1:a=0[vout];")
            a_inputs = "".join(f"[a{i}]" for i in range(count))
            filter_parts.append(f"{a_inputs}concat=n={count}:v=0:a=1[aout]")

        if is_video:
            map_args = ["-map", "[vout]", "-map", "[aout]"]
            codec_args = self._video_codec_args(video_encoder)
        else:
            map_args = ["-map", "[aout]"]
            codec_args = ["-c:a", AUDIO_CODEC_PCM_S16LE]

        return "".join(filter_parts), map_args, codec_args

    @staticmethod
    def _video_codec_args(video_encoder: str) -> list[str]:
        if video_encoder == VIDEO_CODEC_LIBX264:
            return [
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
        # Hardware encoder options (NVENC / QSV / AMF / VideoToolbox / VAAPI)
        return [
            "-c:v",
            video_encoder,
            "-c:a",
            AUDIO_CODEC_AAC,
            "-b:a",
            DEFAULT_AUDIO_BITRATE,
        ]

    def _run_ffmpeg(self, command: list[str]) -> None:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=self._get_clean_env(),
                creationflags=_win_no_window_flags(),
            )
        except subprocess.CalledProcessError as e:
            raise FFmpegExecutionException(f"FFmpeg execution failed:\n{e.stderr}") from e
        except OSError as e:
            raise FFmpegExecutionException(
                f"OS failed to invoke FFmpeg ({self._ffmpeg_path}): {e}"
            ) from e
