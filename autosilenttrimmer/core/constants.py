"""Canonical application constants and defaults."""

from __future__ import annotations

from types import MappingProxyType

# Audio stream defaults
DEFAULT_SAMPLE_RATE_DEEPFILTER: int = 48000
DEFAULT_SAMPLE_RATE_VAD: int = 16000
DEFAULT_AUDIO_CHANNELS_MONO: int = 1
DEFAULT_AUDIO_BITRATE: str = "256k"

# Codecs
AUDIO_CODEC_AAC: str = "aac"
AUDIO_CODEC_PCM_S16LE: str = "pcm_s16le"
AUDIO_CODEC_COPY: str = "copy"
VIDEO_CODEC_COPY: str = "copy"
VIDEO_CODEC_LIBX264: str = "libx264"

# Video encoding parameters
DEFAULT_X264_PRESET: str = "superfast"
DEFAULT_X264_CRF: str = "18"
DEFAULT_X264_BF: str = "0"

# Supported file extensions
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"}
)
AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".wav", ".mp3", ".aac", ".flac", ".ogg", ".m4a"}
)

# VAD parameters
DEFAULT_MIN_SILENCE_GAP_SEC: float = 0.5
DEFAULT_PAD_SEC: float = 0.2

# Energy VAD parameters
DEFAULT_ENERGY_WINDOW_SEC: float = 0.05
DEFAULT_ENERGY_MIN_LEN_SEC: float = 0.2
DEFAULT_ENERGY_PEAK_PERCENTILE: float = 95.0
DEFAULT_ENERGY_DB_OFFSET: float = 25.0
DEFAULT_ENERGY_DILATION_PAD_SEC: float = 0.3
DEFAULT_ENERGY_EPSILON: float = 1e-10

# Silero VAD parameters
DEFAULT_SILERO_REPO: str = "snakers4/silero-vad"
DEFAULT_SILERO_MODEL_NAME: str = "silero_vad"
DEFAULT_SILERO_MIN_SPEECH_DURATION_MS: int = 100

# Whisper VAD parameters
DEFAULT_WHISPER_MODEL_SIZE: str = "base"
DEFAULT_WHISPER_LANGUAGE: str = "id"
DEFAULT_WHISPER_NO_SPEECH_PROB_THRESHOLD: float = 0.6
DEFAULT_WHISPER_MAX_WORD_DURATION_SEC: float = 2.5

# Noise reduction parameters
DEFAULT_SPECTRAL_PROP_DECREASE: float = 0.8
DEFAULT_DEEPFILTER_CHUNK_DURATION_SEC: int = 10

# File suffixes
TEMP_AUDIO_SUFFIX: str = ".wav"
TEMP_VIDEO_SUFFIX: str = ".mkv"
TEMP_SCRIPT_SUFFIX: str = ".txt"
MANIFEST_SUFFIX: str = ".manifest.txt"
PLOT_SUFFIX: str = ".plot.png"

# Scientific plot styling
PLOT_STYLE_THEME: str = "darkgrid"
PLOT_COLOR_BG: str = "#121212"
PLOT_COLOR_GRID: str = "#333333"
PLOT_COLOR_TEXT: str = "white"
PLOT_COLOR_ACTIVE_SPEECH: str = "#00e676"
PLOT_COLOR_DISCARDED: str = "#2c2c2c"
PLOT_COLOR_LEGEND_BG: str = "#1e1e1e"
PLOT_DEFAULT_DPI: int = 300
PLOT_FIG_WIDTH: float = 16.0
PLOT_FIG_HEIGHT: float = 4.0

# Plot configuration map
PLOT_THEME_RC: MappingProxyType[str, str] = MappingProxyType(
    {
        "axes.facecolor": PLOT_COLOR_BG,
        "figure.facecolor": PLOT_COLOR_BG,
        "grid.color": PLOT_COLOR_GRID,
        "text.color": PLOT_COLOR_TEXT,
        "axes.labelcolor": PLOT_COLOR_TEXT,
        "xtick.color": PLOT_COLOR_TEXT,
        "ytick.color": PLOT_COLOR_TEXT,
    }
)

# CLI defaults
DEFAULT_FFMPEG_EXECUTABLE: str | None = None
DEFAULT_NOISE_REDUCTION_METHOD: str = "deepfilter"
DEFAULT_VAD_METHOD: str = "silero"
