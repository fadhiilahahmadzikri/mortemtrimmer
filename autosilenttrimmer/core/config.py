"""Configuration data structures for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from autosilenttrimmer.core.constants import (
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_AUDIO_CHANNELS_MONO,
    DEFAULT_DEEPFILTER_CHUNK_DURATION_SEC,
    DEFAULT_ENERGY_DB_OFFSET,
    DEFAULT_ENERGY_DILATION_PAD_SEC,
    DEFAULT_ENERGY_MIN_LEN_SEC,
    DEFAULT_ENERGY_PEAK_PERCENTILE,
    DEFAULT_ENERGY_WINDOW_SEC,
    DEFAULT_FFMPEG_EXECUTABLE,
    DEFAULT_MIN_SILENCE_GAP_SEC,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_PAD_SEC,
    DEFAULT_SAMPLE_RATE_DEEPFILTER,
    DEFAULT_SAMPLE_RATE_VAD,
    DEFAULT_SILERO_MIN_SPEECH_DURATION_MS,
    DEFAULT_SILERO_MODEL_NAME,
    DEFAULT_SILERO_REPO,
    DEFAULT_SPECTRAL_PROP_DECREASE,
    DEFAULT_VAD_METHOD,
    DEFAULT_WHISPER_LANGUAGE,
    DEFAULT_WHISPER_MAX_WORD_DURATION_SEC,
    DEFAULT_WHISPER_MODEL_SIZE,
    DEFAULT_WHISPER_NO_SPEECH_PROB_THRESHOLD,
    PLOT_COLOR_ACTIVE_SPEECH,
    PLOT_COLOR_BG,
    PLOT_COLOR_DISCARDED,
    PLOT_DEFAULT_DPI,
    PLOT_FIG_HEIGHT,
    PLOT_FIG_WIDTH,
)


@dataclass(frozen=True)
class AudioConfig:
    """Audio configuration parameters."""

    sample_rate_deepfilter: int = DEFAULT_SAMPLE_RATE_DEEPFILTER
    sample_rate_vad: int = DEFAULT_SAMPLE_RATE_VAD
    channels_mono: int = DEFAULT_AUDIO_CHANNELS_MONO
    bitrate: str = DEFAULT_AUDIO_BITRATE


@dataclass(frozen=True)
class VADConfig:
    """Voice activity detection configuration parameters."""

    engine: str = DEFAULT_VAD_METHOD
    min_silence_gap: float = DEFAULT_MIN_SILENCE_GAP_SEC
    pad: float = DEFAULT_PAD_SEC

    # Energy VAD specific
    energy_window_sec: float = DEFAULT_ENERGY_WINDOW_SEC
    energy_min_len_sec: float = DEFAULT_ENERGY_MIN_LEN_SEC
    energy_peak_percentile: float = DEFAULT_ENERGY_PEAK_PERCENTILE
    energy_db_offset: float = DEFAULT_ENERGY_DB_OFFSET
    energy_dilation_pad_sec: float = DEFAULT_ENERGY_DILATION_PAD_SEC

    # Silero VAD specific
    silero_repo: str = DEFAULT_SILERO_REPO
    silero_model: str = DEFAULT_SILERO_MODEL_NAME
    silero_min_speech_duration_ms: int = DEFAULT_SILERO_MIN_SPEECH_DURATION_MS

    # Whisper VAD specific
    whisper_model_size: str = DEFAULT_WHISPER_MODEL_SIZE
    whisper_language: str = DEFAULT_WHISPER_LANGUAGE
    whisper_no_speech_threshold: float = DEFAULT_WHISPER_NO_SPEECH_PROB_THRESHOLD
    whisper_max_word_duration_sec: float = DEFAULT_WHISPER_MAX_WORD_DURATION_SEC


@dataclass(frozen=True)
class NoiseReductionConfig:
    """Noise reduction configuration parameters."""

    method: str = DEFAULT_NOISE_REDUCTION_METHOD
    spectral_prop_decrease: float = DEFAULT_SPECTRAL_PROP_DECREASE
    chunk_duration_sec: int = DEFAULT_DEEPFILTER_CHUNK_DURATION_SEC


@dataclass(frozen=True)
class VisualizerConfig:
    """Timeline visualizer configuration parameters."""

    dpi: int = PLOT_DEFAULT_DPI
    fig_width: float = PLOT_FIG_WIDTH
    fig_height: float = PLOT_FIG_HEIGHT
    speech_color: str = PLOT_COLOR_ACTIVE_SPEECH
    silence_color: str = PLOT_COLOR_DISCARDED
    bg_color: str = PLOT_COLOR_BG


@dataclass(frozen=True)
class MediaProcessingConfig:
    """Aggregate configuration for processing pipeline."""

    ffmpeg_path: str | None = DEFAULT_FFMPEG_EXECUTABLE
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    noise_reduction: NoiseReductionConfig = field(default_factory=NoiseReductionConfig)
    visualizer: VisualizerConfig = field(default_factory=VisualizerConfig)
