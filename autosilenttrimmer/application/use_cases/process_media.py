"""Process media use case: orchestrates audio extraction, VAD, slicing, and denoising."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import soundfile as sf

from autosilenttrimmer.core.constants import (
    MANIFEST_SUFFIX,
    TEMP_AUDIO_SUFFIX,
    TEMP_VIDEO_SUFFIX,
    VIDEO_EXTENSIONS,
)
from autosilenttrimmer.core.exceptions import (
    FormatMismatchException,
    MediaFileNotFoundException,
)
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.contracts.visualizer import IVisualizer
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.domain.models.processing_result import ProcessingResult

logger = logging.getLogger(__name__)


class ProcessMediaUseCase:
    """Use case to execute the full audio/video silence trimming and noise reduction pipeline."""

    def __init__(
        self,
        media_manager: IMediaManager,
        vad_strategy: IVoiceActivityDetector | None = None,
        noise_reduction_strategy: INoiseReductionStrategy | None = None,
        visualizer: IVisualizer | None = None,
    ) -> None:
        self._media_manager = media_manager
        self._vad_strategy = vad_strategy
        self._noise_reduction_strategy = noise_reduction_strategy
        self._visualizer = visualizer

    def execute(self, input_path: str, output_path: str) -> ProcessingResult:
        """Execute the end-to-end processing pipeline."""
        if not os.path.exists(input_path):
            raise MediaFileNotFoundException(f"Input file does not exist: {input_path}")

        _, in_ext = os.path.splitext(input_path.lower())
        _, out_ext = os.path.splitext(output_path.lower())

        is_input_video = in_ext in VIDEO_EXTENSIONS
        is_output_video = out_ext in VIDEO_EXTENSIONS

        if not is_input_video and is_output_video:
            raise FormatMismatchException(
                f"Format Mismatch Error: Input is an audio file '{in_ext}', "
                f"but output is set to a video container '{out_ext}'. "
                "Please specify an audio extension (e.g., .wav, .aac, .mp3) for the output."
            )

        fd_raw, raw_audio = tempfile.mkstemp(suffix=TEMP_AUDIO_SUFFIX)
        os.close(fd_raw)

        try:
            if is_input_video:
                self._media_manager.extract_audio(input_path, raw_audio)
                target_audio = raw_audio
            else:
                target_audio = input_path
                shutil.copy(input_path, raw_audio)

            audio_info = sf.info(target_audio)
            original_duration = float(audio_info.duration)

            segments: list[MediaSegment] = []
            manifest_path: str | None = None

            if self._vad_strategy:
                manifest_path = output_path + MANIFEST_SUFFIX
                logger.info("Executing Voice Activity Detection...")
                segments = self._vad_strategy.get_keep_segments(
                    target_audio, manifest_path
                )
                logger.info("VAD detected %d speech segments.", len(segments))

            cut_suffix = TEMP_VIDEO_SUFFIX if is_input_video else TEMP_AUDIO_SUFFIX
            fd_cut, cut_media = tempfile.mkstemp(suffix=cut_suffix)
            os.close(fd_cut)

            try:
                if self._vad_strategy:
                    self._media_manager.slice_and_concat(
                        input_path, segments, cut_media
                    )
                    final_duration = sum(s.duration for s in segments)
                else:
                    shutil.copy(input_path, cut_media)
                    final_duration = original_duration

                if self._noise_reduction_strategy:
                    fd_cut_raw, cut_raw_audio = tempfile.mkstemp(suffix=TEMP_AUDIO_SUFFIX)
                    fd_cut_clean, cut_clean_audio = tempfile.mkstemp(suffix=TEMP_AUDIO_SUFFIX)
                    os.close(fd_cut_raw)
                    os.close(fd_cut_clean)

                    try:
                        if is_input_video:
                            self._media_manager.extract_audio(cut_media, cut_raw_audio)
                            audio_to_enhance = cut_raw_audio
                        else:
                            audio_to_enhance = cut_media

                        logger.info("Executing noise reduction...")
                        self._noise_reduction_strategy.process(
                            audio_to_enhance, cut_clean_audio
                        )

                        if is_input_video:
                            self._media_manager.merge_audio(
                                cut_media, cut_clean_audio, output_path
                            )
                        else:
                            self._media_manager.export_audio(
                                cut_clean_audio, output_path
                            )
                    finally:
                        if os.path.exists(cut_raw_audio):
                            os.remove(cut_raw_audio)
                        if os.path.exists(cut_clean_audio):
                            os.remove(cut_clean_audio)
                else:
                    if is_input_video:
                        shutil.copy(cut_media, output_path)
                    else:
                        self._media_manager.export_audio(cut_media, output_path)

            finally:
                if os.path.exists(cut_media):
                    os.remove(cut_media)

            plot_path: str | None = None
            if self._vad_strategy and self._visualizer:
                logger.info("Generating timeline plot...")
                plot_path = self._visualizer.generate_timeline_plot(
                    segments, original_duration, output_path
                )

            silence_removed = max(0.0, original_duration - final_duration)
            reduction_percentage = (
                (silence_removed / original_duration) * 100.0
                if original_duration > 0
                else 0.0
            )

            return ProcessingResult(
                input_path=input_path,
                output_path=output_path,
                original_duration=original_duration,
                final_duration=final_duration,
                silence_removed_duration=silence_removed,
                reduction_percentage=reduction_percentage,
                segments_retained_count=len(segments),
                manifest_path=manifest_path,
                plot_path=plot_path,
            )

        finally:
            if os.path.exists(raw_audio):
                os.remove(raw_audio)
