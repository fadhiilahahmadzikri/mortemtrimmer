# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Silero neural acoustic Voice Activity Detection."""

from __future__ import annotations

import logging

from tqdm import tqdm

from autosilenttrimmer.core.config import VADConfig
from autosilenttrimmer.core.constants import SUPPORTED_VAD_SAMPLE_RATES
from autosilenttrimmer.core.exceptions import DependencyMissingException
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.entities.segment import MediaSegment
from autosilenttrimmer.infrastructure.runtime.model_paths import resolve_offline_silero_dir

logger = logging.getLogger(__name__)


class SileroBasedVAD(IVoiceActivityDetector):
    """Silero neural acoustic VAD implementation."""

    def __init__(self, config: VADConfig | None = None) -> None:
        self._config = config or VADConfig()

    def get_keep_segments(
        self, audio_path: str, manifest_path: str | None = None
    ) -> list[MediaSegment]:
        sr_vad = self._config.sample_rate_vad
        if sr_vad not in SUPPORTED_VAD_SAMPLE_RATES:
            raise ValueError(
                f"Silero VAD supports only sample rates {SUPPORTED_VAD_SAMPLE_RATES}, got {sr_vad}."
            )

        try:
            import torch
        except ImportError as exc:
            raise DependencyMissingException(
                "PyTorch is required for Silero VAD. Run --setup-runtime to install AI Runtime Pack."
            ) from exc

        offline_dir = resolve_offline_silero_dir()
        if offline_dir is not None:
            logger.info("Loading bundled offline Silero VAD model from: %s", offline_dir)
            model, utils = torch.hub.load(
                repo_or_dir=offline_dir,
                model=self._config.silero_model,
                source="local",
                trust_repo=True,
            )
        else:
            logger.info("Loading Silero VAD neural model...")
            model, utils = torch.hub.load(
                repo_or_dir=self._config.silero_repo,
                model=self._config.silero_model,
                force_reload=False,
                trust_repo=True,
            )
        get_speech_timestamps, _, read_audio, _, _ = utils

        logger.info("Reading acoustic wave data (%d Hz)...", sr_vad)
        wav = read_audio(audio_path, sampling_rate=sr_vad)

        logger.info("Analyzing voice activity timestamps...")
        min_silence_ms = int(self._config.min_silence_gap * 1000)

        speech_timestamps = get_speech_timestamps(
            wav,
            model,
            sampling_rate=sr_vad,
            min_silence_duration_ms=min_silence_ms,
            min_speech_duration_ms=self._config.silero_min_speech_duration_ms,
        )

        raw_segments: list[MediaSegment] = []
        manifest_lines: list[str] = []

        for seg in tqdm(speech_timestamps, desc="Silero Segmentation", unit=" segment"):
            start_sec = seg["start"] / float(sr_vad)
            end_sec = seg["end"] / float(sr_vad)

            start_padded = max(0.0, start_sec - self._config.pad)
            end_padded = end_sec + self._config.pad

            manifest_lines.append(f"[{start_sec:.3f} -> {end_sec:.3f}] Speech Detected")
            raw_segments.append(MediaSegment(start=start_padded, end=end_padded))

        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines))

        return MediaSegment.merge_overlapping(raw_segments)
