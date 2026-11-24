"""Energy-based voice activity detection."""

from __future__ import annotations

import logging

import numpy as np
import soundfile as sf

from autosilenttrimmer.core.config import VADConfig
from autosilenttrimmer.core.constants import DEFAULT_ENERGY_EPSILON
from autosilenttrimmer.domain.contracts.vad import IVoiceActivityDetector
from autosilenttrimmer.domain.entities.segment import MediaSegment

logger = logging.getLogger(__name__)


class EnergyBasedVAD(IVoiceActivityDetector):
    """Lightweight VAD based on signal frame power thresholding."""

    def __init__(self, config: VADConfig | None = None) -> None:
        self._config = config or VADConfig()

    def get_keep_segments(
        self, audio_path: str, manifest_path: str | None = None
    ) -> list[MediaSegment]:
        logger.info("Running Energy-based VAD analysis...")
        audio, sample_rate = sf.read(audio_path, dtype="float32")

        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        window_sec = self._config.energy_window_sec
        window_size = int(sample_rate * window_sec)
        if len(audio) == 0:
            return []

        pad_len = window_size - (len(audio) % window_size)
        if pad_len != window_size:
            audio = np.pad(audio, (0, pad_len))

        frames = audio.reshape(-1, window_size)
        power = np.mean(frames**2, axis=1)
        decibels = 10 * np.log10(power + DEFAULT_ENERGY_EPSILON)
        peak_db = float(np.percentile(decibels, self._config.energy_peak_percentile))
        threshold_db = peak_db - self._config.energy_db_offset
        is_speech = decibels > threshold_db

        pad_frames = int(self._config.energy_dilation_pad_sec / window_sec)
        kernel = np.ones(pad_frames * 2 + 1)
        dilated = np.convolve(is_speech.astype(int), kernel, mode="same") > 0

        diff = np.diff(np.concatenate([[0], dilated.astype(int), [0]]))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]

        segments: list[MediaSegment] = []
        actual_duration = len(audio) / sample_rate

        for s, e in zip(starts, ends):
            start_sec = s * window_sec
            end_sec = min(e * window_sec, actual_duration)
            if end_sec - start_sec >= self._config.energy_min_len_sec:
                segments.append(MediaSegment(start=start_sec, end=end_sec))

        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                for seg in segments:
                    f.write(f"[{seg.start:.3f} - {seg.end:.3f}]\n")

        return segments
