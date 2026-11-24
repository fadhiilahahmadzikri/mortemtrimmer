# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Persistent user application settings domain model and config mapper."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from autosilenttrimmer.core.config import (
    AudioConfig,
    ExecutionConfig,
    MediaProcessingConfig,
    NoiseReductionConfig,
    OutputPolicyConfig,
    RuntimeConfig,
    UIConfig,
    VADConfig,
)
from autosilenttrimmer.core.constants import (
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_CHUNK_MAX_RETRIES,
    DEFAULT_COMPUTE_POLICY,
    DEFAULT_DEEPFILTER_CHUNK_DURATION_SEC,
    DEFAULT_ENERGY_DB_OFFSET,
    DEFAULT_ENERGY_DILATION_PAD_SEC,
    DEFAULT_ENERGY_MIN_LEN_SEC,
    DEFAULT_ENERGY_PEAK_PERCENTILE,
    DEFAULT_ENERGY_WINDOW_SEC,
    DEFAULT_LANGUAGE,
    DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT,
    DEFAULT_MIN_SILENCE_GAP_SEC,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_ON_CONFLICT,
    DEFAULT_OUTPUT_LOCATION,
    DEFAULT_OUTPUT_NAMING_TEMPLATE,
    DEFAULT_PAD_SEC,
    DEFAULT_RELEASE_CHANNEL,
    DEFAULT_RELEASE_MANIFEST_URL,
    DEFAULT_SAMPLE_RATE_DEEPFILTER,
    DEFAULT_SAMPLE_RATE_VAD,
    DEFAULT_SILERO_MIN_SPEECH_DURATION_MS,
    DEFAULT_SPECTRAL_PROP_DECREASE,
    DEFAULT_TRIM_STRATEGY,
    DEFAULT_VAD_METHOD,
    DEFAULT_WHISPER_LANGUAGE,
    DEFAULT_WHISPER_MAX_WORD_DURATION_SEC,
    DEFAULT_WHISPER_MODEL_SIZE,
    DEFAULT_WHISPER_NO_SPEECH_PROB_THRESHOLD,
    DEFAULT_X264_CRF,
    DEFAULT_X264_PRESET,
    DISK_SPACE_SAFETY_FACTOR,
    IPC_COALESCE_WINDOW_SEC,
    MIN_CHUNKABLE_DURATION_SEC,
    TARGET_CHUNK_MAX_SEC,
    TARGET_CHUNK_MIN_SEC,
    VERIFY_DURATION_TOLERANCE_SEC,
)
from autosilenttrimmer.core.settings_schema import SETTINGS_BY_KEY, ControlType


@dataclass(frozen=True)
class UserSettings:
    """User-configurable preferences stored atomically in settings.json."""

    # General & Pipeline
    trim_strategy: str = DEFAULT_TRIM_STRATEGY
    vad_engine: str = DEFAULT_VAD_METHOD
    noise_reduction_method: str = DEFAULT_NOISE_REDUCTION_METHOD
    language: str = DEFAULT_LANGUAGE
    enable_notifications: bool = True
    generate_visual_artifacts: bool = False

    # VAD & Engines
    min_silence_gap: float = DEFAULT_MIN_SILENCE_GAP_SEC
    pad: float = DEFAULT_PAD_SEC
    silero_min_speech_duration_ms: int = DEFAULT_SILERO_MIN_SPEECH_DURATION_MS
    whisper_model_size: str = DEFAULT_WHISPER_MODEL_SIZE
    whisper_language: str = DEFAULT_WHISPER_LANGUAGE
    whisper_no_speech_threshold: float = DEFAULT_WHISPER_NO_SPEECH_PROB_THRESHOLD
    whisper_max_word_duration_sec: float = DEFAULT_WHISPER_MAX_WORD_DURATION_SEC
    energy_window_sec: float = DEFAULT_ENERGY_WINDOW_SEC
    energy_min_len_sec: float = DEFAULT_ENERGY_MIN_LEN_SEC
    energy_peak_percentile: float = DEFAULT_ENERGY_PEAK_PERCENTILE
    energy_db_offset: float = DEFAULT_ENERGY_DB_OFFSET
    energy_dilation_pad_sec: float = DEFAULT_ENERGY_DILATION_PAD_SEC
    spectral_prop_decrease: float = DEFAULT_SPECTRAL_PROP_DECREASE
    deepfilter_chunk_duration_sec: int = DEFAULT_DEEPFILTER_CHUNK_DURATION_SEC

    # Encoder & Chunking
    compute_policy: str = DEFAULT_COMPUTE_POLICY
    max_workers: int | None = None
    frame_accurate: bool = True
    x264_preset: str = DEFAULT_X264_PRESET
    x264_crf: int = int(DEFAULT_X264_CRF)
    audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    sample_rate_vad: int = DEFAULT_SAMPLE_RATE_VAD
    sample_rate_deepfilter: int = DEFAULT_SAMPLE_RATE_DEEPFILTER
    target_chunk_min_sec: float = TARGET_CHUNK_MIN_SEC
    target_chunk_max_sec: float = TARGET_CHUNK_MAX_SEC
    min_chunkable_duration_sec: float = MIN_CHUNKABLE_DURATION_SEC
    chunk_max_retries: int = DEFAULT_CHUNK_MAX_RETRIES
    verify_duration_tolerance_sec: float = VERIFY_DURATION_TOLERANCE_SEC

    # Output & Paths
    output_location: str = DEFAULT_OUTPUT_LOCATION
    output_custom_dir: str | None = None
    output_naming_template: str = DEFAULT_OUTPUT_NAMING_TEMPLATE
    on_conflict: str = DEFAULT_ON_CONFLICT
    disk_space_safety_factor: float = DISK_SPACE_SAFETY_FACTOR

    # System & Runtime
    background_priority: bool = True
    pause_on_low_battery: bool = True
    low_battery_threshold_percent: float = DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT
    ipc_coalesce_window_sec: float = IPC_COALESCE_WINDOW_SEC
    ffmpeg_path: str | None = None
    update_channel: str = DEFAULT_RELEASE_CHANNEL
    manifest_url: str = DEFAULT_RELEASE_MANIFEST_URL

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings cleanly to plain dictionary."""
        return asdict(self)

    def to_processing_config(
        self,
        *,
        ffmpeg_override: str | None = None,
    ) -> MediaProcessingConfig:
        """Map persisted UserSettings into runtime MediaProcessingConfig contract."""
        effective_ffmpeg = ffmpeg_override or (
            self.ffmpeg_path.strip() if self.ffmpeg_path and self.ffmpeg_path.strip() else None
        )
        return MediaProcessingConfig(
            ffmpeg_path=effective_ffmpeg,
            audio=AudioConfig(
                sample_rate_deepfilter=self.sample_rate_deepfilter,
                sample_rate_vad=self.sample_rate_vad,
                bitrate=self.audio_bitrate,
                x264_preset=self.x264_preset,
                x264_crf=str(self.x264_crf),
            ),
            vad=VADConfig(
                engine=self.vad_engine,
                min_silence_gap=self.min_silence_gap,
                pad=self.pad,
                sample_rate_vad=self.sample_rate_vad,
                energy_window_sec=self.energy_window_sec,
                energy_min_len_sec=self.energy_min_len_sec,
                energy_peak_percentile=self.energy_peak_percentile,
                energy_db_offset=self.energy_db_offset,
                energy_dilation_pad_sec=self.energy_dilation_pad_sec,
                silero_min_speech_duration_ms=self.silero_min_speech_duration_ms,
                whisper_model_size=self.whisper_model_size,
                whisper_language=self.whisper_language,
                whisper_no_speech_threshold=self.whisper_no_speech_threshold,
                whisper_max_word_duration_sec=self.whisper_max_word_duration_sec,
            ),
            noise_reduction=NoiseReductionConfig(
                method=self.noise_reduction_method,
                spectral_prop_decrease=self.spectral_prop_decrease,
                chunk_duration_sec=self.deepfilter_chunk_duration_sec,
            ),
            execution=ExecutionConfig(
                strategy=self.trim_strategy,
                compute_policy=self.compute_policy,
                max_workers=self.max_workers,
                background_priority=self.background_priority,
                pause_on_low_battery=self.pause_on_low_battery,
                low_battery_threshold_percent=self.low_battery_threshold_percent,
                target_chunk_min_sec=self.target_chunk_min_sec,
                target_chunk_max_sec=self.target_chunk_max_sec,
                min_chunkable_duration_sec=self.min_chunkable_duration_sec,
                chunk_max_retries=self.chunk_max_retries,
                verify_duration_tolerance_sec=self.verify_duration_tolerance_sec,
                frame_accurate=self.frame_accurate,
            ),
            output_policy=OutputPolicyConfig(
                location=self.output_location,
                custom_dir=(
                    self.output_custom_dir.strip()
                    if self.output_custom_dir and self.output_custom_dir.strip()
                    else None
                ),
                naming_template=self.output_naming_template or DEFAULT_OUTPUT_NAMING_TEMPLATE,
                on_conflict=self.on_conflict,
                disk_space_safety_factor=self.disk_space_safety_factor,
            ),
            runtime=RuntimeConfig(
                manifest_url=self.manifest_url or DEFAULT_RELEASE_MANIFEST_URL,
                channel=self.update_channel,
            ),
            ui=UIConfig(
                language=self.language,
                enable_notifications=self.enable_notifications,
                generate_visual_artifacts=self.generate_visual_artifacts,
            ),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserSettings:
        """Deserialize, sanitize types/bounds against schema, and ignore unknown keys."""
        sanitized: dict[str, Any] = {}
        valid_fields = set(cls.__dataclass_fields__)

        for key, raw_val in data.items():
            if key not in valid_fields:
                continue
            spec = SETTINGS_BY_KEY.get(key)
            if spec is None:
                sanitized[key] = raw_val
                continue

            if key == "max_workers":
                if raw_val is None or raw_val == 0:
                    sanitized[key] = None
                else:
                    val = int(raw_val)
                    max_w = int(spec.max_val) if spec.max_val is not None else 32
                    sanitized[key] = max(1, min(max_w, val))
            elif spec.control_type == ControlType.BOOL:
                sanitized[key] = bool(raw_val)
            elif spec.control_type == ControlType.INT:
                try:
                    num = int(raw_val)
                    if spec.min_val is not None:
                        num = max(int(spec.min_val), num)
                    if spec.max_val is not None:
                        num = min(int(spec.max_val), num)
                    sanitized[key] = num
                except (TypeError, ValueError):
                    sanitized[key] = spec.default
            elif spec.control_type == ControlType.FLOAT:
                try:
                    fnum = float(raw_val)
                    if spec.min_val is not None:
                        fnum = max(float(spec.min_val), fnum)
                    if spec.max_val is not None:
                        fnum = min(float(spec.max_val), fnum)
                    sanitized[key] = fnum
                except (TypeError, ValueError):
                    sanitized[key] = spec.default
            elif spec.control_type == ControlType.CHOICE:
                sval = str(raw_val)
                sanitized[key] = sval if sval in spec.choices else spec.default
            elif spec.control_type in {ControlType.PATH_DIR, ControlType.PATH_FILE}:
                text = str(raw_val).strip() if raw_val is not None else ""
                sanitized[key] = text or None
            else:
                sanitized[key] = str(raw_val) if raw_val is not None else spec.default

        return cls(**sanitized)
