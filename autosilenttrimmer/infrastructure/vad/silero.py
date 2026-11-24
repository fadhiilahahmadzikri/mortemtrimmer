"""Silero neural acoustic Voice Activity Detection."""

from __future__ import annotations

import logging

from tqdm import tqdm

from autosilenttrimmer.core.config import VADConfig
from autosilenttrimmer.core.constants import DEFAULT_SAMPLE_RATE_VAD
from autosilenttrimmer.core.exceptions import DependencyMissingException
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.entities.segment import MediaSegment

logger = logging.getLogger(__name__)


class SileroBasedVAD(IVoiceActivityDetector):
    """Silero neural acoustic VAD implementation."""

    def __init__(self, config: VADConfig | None = None) -> None:
        self._config = config or VADConfig()

    def get_keep_segments(
        self, audio_path: str, manifest_path: str | None = None
    ) -> list[MediaSegment]:
        try:
            import torch
        except ImportError as exc:
            raise DependencyMissingException(
                "PyTorch is required for Silero VAD. Run --setup-runtime to install AI Runtime Pack."
            ) from exc

        logger.info("Loading Silero VAD neural model...")
        model, utils = torch.hub.load(
            repo_or_dir=self._config.silero_repo,
            model=self._config.silero_model,
            force_reload=False,
            trust_repo=True,
        )
        get_speech_timestamps, _, read_audio, _, _ = utils

        logger.info("Reading acoustic wave data...")
        wav = read_audio(audio_path, sampling_rate=DEFAULT_SAMPLE_RATE_VAD)

        logger.info("Analyzing voice activity timestamps...")
        min_silence_ms = int(self._config.min_silence_gap * 1000)

        speech_timestamps = get_speech_timestamps(
            wav,
            model,
            sampling_rate=DEFAULT_SAMPLE_RATE_VAD,
            min_silence_duration_ms=min_silence_ms,
            min_speech_duration_ms=self._config.silero_min_speech_duration_ms,
        )

        raw_segments: list[MediaSegment] = []
        manifest_lines: list[str] = []

        for seg in tqdm(speech_timestamps, desc="Silero Segmentation", unit=" segment"):
            start_sec = seg["start"] / float(DEFAULT_SAMPLE_RATE_VAD)
            end_sec = seg["end"] / float(DEFAULT_SAMPLE_RATE_VAD)

            start_padded = max(0.0, start_sec - self._config.pad)
            end_padded = end_sec + self._config.pad

            manifest_lines.append(f"[{start_sec:.3f} -> {end_sec:.3f}] Speech Detected")
            raw_segments.append(MediaSegment(start=start_padded, end=end_padded))

        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines))

        return MediaSegment.merge_overlapping(raw_segments)
