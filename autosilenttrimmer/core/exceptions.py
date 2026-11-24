"""Custom domain and infrastructure exceptions."""


class AutoSilentTrimmerException(Exception):
    """Base exception for all domain and pipeline errors."""


class MediaProcessingException(AutoSilentTrimmerException):
    """Exception raised during media extraction, trimming, or multiplexing."""


class FormatMismatchException(MediaProcessingException):
    """Exception raised when media container formats are incompatible."""


class MediaFileNotFoundException(MediaProcessingException):
    """Exception raised when an input media file does not exist."""


class FFmpegExecutionException(MediaProcessingException):
    """Exception raised when FFmpeg fails during execution."""


class VoiceActivityDetectionException(MediaProcessingException):
    """Exception raised during VAD analysis."""


class NoiseReductionException(MediaProcessingException):
    """Exception raised during noise reduction processing."""


class DependencyMissingException(AutoSilentTrimmerException):
    """Exception raised when a required third-party dependency is missing."""
