"""Whisper semantic Voice Activity Detection."""

from __future__ import annotations

import logging

from tqdm import tqdm

from autosilenttrimmer.core.config import VADConfig
from autosilenttrimmer.core.exceptions import DependencyMissingException
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.infrastructure.runtime.model_paths import resolve_offline_whisper_dir

logger = logging.getLogger(__name__)


class WhisperBasedVAD(IVoiceActivityDetector):
    """Faster-Whisper semantic VAD with word-level timestamp extraction."""

    def __init__(self, config: VADConfig | None = None, device: str | None = None) -> None:
        self._config = config or VADConfig()
        self._device = device

    def get_keep_segments(
        self, audio_path: str, manifest_path: str | None = None
    ) -> list[MediaSegment]:
        try:
            import torch
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise DependencyMissingException(
                "Missing dependency 'faster-whisper' or 'torch' for Semantic VAD."
            ) from e

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        compute_type = "float16" if device == "cuda" else "int8"

        offline_dir = resolve_offline_whisper_dir(self._config.whisper_model_size)
        if offline_dir is not None:
            logger.info(
                "Loading bundled offline Whisper model (%s -> %s on %s, compute: %s)...",
                self._config.whisper_model_size,
                offline_dir,
                device.upper(),
                compute_type,
            )
            model = WhisperModel(
                offline_dir,
                device=device,
                compute_type=compute_type,
                local_files_only=True,
            )
        else:
            logger.info(
                "Loading Whisper model (%s on %s, compute: %s)...",
                self._config.whisper_model_size,
                device.upper(),
                compute_type,
            )
            model = WhisperModel(
                self._config.whisper_model_size,
                device=device,
                compute_type=compute_type,
            )

        logger.info(
            "Transcribing audio for semantic timestamps (language: %s)...",
            self._config.whisper_language,
        )
        segments_gen, _ = model.transcribe(
            audio_path,
            language=self._config.whisper_language,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
        )

        raw_segments: list[MediaSegment] = []
        manifest_lines: list[str] = []

        for segment in tqdm(segments_gen, desc="Whisper Semantic Analysis", unit=" segment"):
            if (
                segment.no_speech_prob > self._config.whisper_no_speech_threshold
                or not segment.text.strip()
                or not segment.words
            ):
                continue

            manifest_lines.append(
                f"[{segment.start:.3f} -> {segment.end:.3f}] {segment.text.strip()} "
                f"(P_NoSpeech: {segment.no_speech_prob:.2f})"
            )

            for word in segment.words:
                if not word.word.strip() or (
                    word.end - word.start > self._config.whisper_max_word_duration_sec
                ):
                    continue
                manifest_lines.append(
                    f"    [{word.start:.3f} -> {word.end:.3f}] {word.word.strip()}"
                )
                start_padded = max(0.0, word.start - self._config.pad)
                end_padded = word.end + self._config.pad
                raw_segments.append(MediaSegment(start=start_padded, end=end_padded))

        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines))

        return MediaSegment.merge_overlapping(raw_segments, min_gap=self._config.min_silence_gap)
