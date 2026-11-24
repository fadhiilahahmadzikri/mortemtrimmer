"""Canonical application constants and defaults."""

from __future__ import annotations

from types import MappingProxyType

# Application identity
APP_SHORT_NAME: str = "Mortem"
APP_NAME: str = "Mortem Primer"
SHELL_CONTEXT_MENU_LABEL: str = "Trim This Video"
APP_SLUG: str = "autosilenttrimmer"
APP_VERSION: str = "1.0.0"
APP_USER_MODEL_ID: str = "MortemPrimer.DesktopApp.1"
DEFAULT_LANGUAGE: str = "en"
SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"en", "id"})

# Audio stream defaults
DEFAULT_SAMPLE_RATE_DEEPFILTER: int = 48000
DEFAULT_SAMPLE_RATE_VAD: int = 16000
SUPPORTED_VAD_SAMPLE_RATES: tuple[int, ...] = (8000, 16000)
DEFAULT_AUDIO_CHANNELS_MONO: int = 1
DEFAULT_AUDIO_BITRATE: str = "256k"

# Codecs & encoders
AUDIO_CODEC_AAC: str = "aac"
AUDIO_CODEC_PCM_S16LE: str = "pcm_s16le"
AUDIO_CODEC_COPY: str = "copy"
VIDEO_CODEC_COPY: str = "copy"
VIDEO_CODEC_LIBX264: str = "libx264"
HW_ENCODER_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("nvenc", "h264_nvenc"),
    ("qsv", "h264_qsv"),
    ("amf", "h264_amf"),
    ("videotoolbox", "h264_videotoolbox"),
    ("vaapi", "h264_vaapi"),
)

# Video encoding & choice tuples
DEFAULT_X264_PRESET: str = "superfast"
DEFAULT_X264_CRF: str = "18"
DEFAULT_X264_BF: str = "0"
SUPPORTED_X264_PRESETS: tuple[str, ...] = (
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
)
SUPPORTED_AUDIO_BITRATES: tuple[str, ...] = ("128k", "192k", "256k", "320k")
SUPPORTED_WHISPER_MODELS: tuple[str, ...] = ("tiny", "base", "small", "medium", "large-v3")
SUPPORTED_TRIM_STRATEGIES: tuple[str, ...] = ("auto-silence", "manual-range")
SUPPORTED_VAD_ENGINES: tuple[str, ...] = ("silero", "whisper", "energy", "none")
SUPPORTED_NOISE_METHODS: tuple[str, ...] = ("none", "spectral", "deepfilter")
SUPPORTED_COMPUTE_POLICIES: tuple[str, ...] = ("g2_gpu_preferred", "g1_hard_gate", "g3_cpu_only")
SUPPORTED_OUTPUT_LOCATIONS: tuple[str, ...] = ("beside-source", "custom")
SUPPORTED_CONFLICT_MODES: tuple[str, ...] = ("increment", "overwrite")
SUPPORTED_RELEASE_CHANNELS: tuple[str, ...] = ("stable", "beta")
DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT: float = 20.0
TUNE_WINDOW_LOCK_FILENAME: str = "autosilenttrimmer_tune.lock"

# Supported file extension tiers (Doc 01 §11)
TIER1_VIDEO_EXTENSIONS: frozenset[str] = frozenset({".mp4", ".mkv", ".mov", ".webm"})
TIER2_VIDEO_EXTENSIONS: frozenset[str] = frozenset({".m4v", ".ts", ".mts", ".m2ts", ".avi", ".flv"})
VIDEO_EXTENSIONS: frozenset[str] = TIER1_VIDEO_EXTENSIONS | TIER2_VIDEO_EXTENSIONS
AUDIO_EXTENSIONS: frozenset[str] = frozenset({".wav", ".mp3", ".aac", ".flac", ".ogg", ".m4a"})
SUPPORTED_MEDIA_EXTENSIONS: frozenset[str] = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

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

# Parallel chunking, verification & execution policy
TARGET_CHUNK_MIN_SEC: float = 30.0
TARGET_CHUNK_MAX_SEC: float = 120.0
MIN_CHUNKABLE_DURATION_SEC: float = 45.0
ANALYZE_CONTEXT_OVERLAP_SEC: float = 2.0
DEFAULT_RESERVED_CPU_CORES: int = 2
ESTIMATED_MEMORY_PER_WORKER_MB: int = 512
DEFAULT_IO_BOUND_CONCURRENCY: int = 2
DEFAULT_GPU_MAX_SESSIONS: int = 2
DEFAULT_CHUNK_MAX_RETRIES: int = 2
VERIFY_DURATION_TOLERANCE_SEC: float = 0.75
DEFAULT_COMPUTE_POLICY: str = "g2_gpu_preferred"
DEFAULT_TRIM_STRATEGY: str = "auto-silence"

# Non-destructive output policy & safety guards
DEFAULT_OUTPUT_NAMING_TEMPLATE: str = "{name}.trimmed.{ext}"
DEFAULT_OUTPUT_LOCATION: str = "beside-source"
DEFAULT_ON_CONFLICT: str = "increment"
DISK_SPACE_SAFETY_FACTOR: float = 2.2
MIN_FREE_DISK_BYTES: int = 100 * 1024 * 1024

# File suffixes
TEMP_AUDIO_SUFFIX: str = ".wav"
TEMP_VIDEO_SUFFIX: str = ".mkv"
TEMP_SCRIPT_SUFFIX: str = ".txt"
MANIFEST_SUFFIX: str = ".manifest.txt"
PLOT_SUFFIX: str = ".plot.png"

# IPC & shell integration
IPC_PIPE_NAME_WINDOWS: str = r"\\.\pipe\autosilenttrimmer_gateway"
IPC_SOCKET_FILENAME: str = "autosilenttrimmer_gateway.sock"
IPC_COALESCE_WINDOW_SEC: float = 0.25
IPC_CONNECT_TIMEOUT_SEC: float = 3.0
SINGLE_INSTANCE_LOCK_FILENAME: str = "autosilenttrimmer.lock"
SHELL_REGISTRY_MENU_KEY: str = "TrimThisVideo"

# Runtime pack & release manifest
RELEASE_MANIFEST_SCHEMA_VERSION: str = "1.0"
DEFAULT_RELEASE_CHANNEL: str = "stable"
DEFAULT_RELEASE_MANIFEST_URL: str = "https://github.com/fadhiilahahmadzikri/autosilenttrimmer/releases/latest/download/release-manifest.json"
RUNTIME_DOWNLOAD_CHUNK_BYTES: int = 256 * 1024
RUNTIME_DOWNLOAD_TIMEOUT_SEC: float = 30.0
RUNTIME_PUBLIC_KEY_ENV: str = "AUTOSILENTTRIMMER_MANIFEST_PUBKEY"

# Tray & UI styling
TRAY_POLL_INTERVAL_SEC: float = 0.25
ETA_SMOOTHING_ALPHA: float = 0.3

# Scientific plot styling
PLOT_STYLE_THEME: str = "darkgrid"
PLOT_COLOR_BG: str = "#14100E"
PLOT_COLOR_GRID: str = "#3A2B20"
PLOT_COLOR_TEXT: str = "#F4EAD5"
PLOT_COLOR_ACTIVE_SPEECH: str = "#E2A634"
PLOT_COLOR_DISCARDED: str = "#292019"
PLOT_COLOR_LEGEND_BG: str = "#1E1713"
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
DEFAULT_NOISE_REDUCTION_METHOD: str = "none"
DEFAULT_VAD_METHOD: str = "silero"
