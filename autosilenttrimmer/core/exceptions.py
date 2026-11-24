"""Canonical error taxonomy and domain exception hierarchy."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Stable machine-readable error codes for UI, diagnostics, and telemetry."""

    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    NO_COMPUTE_BACKEND = "NO_COMPUTE_BACKEND"
    RUNTIME_MISSING = "RUNTIME_MISSING"
    DISK_FULL = "DISK_FULL"
    SOURCE_LOCKED = "SOURCE_LOCKED"
    CHUNK_FAILED = "CHUNK_FAILED"
    MERGE_FAILED = "MERGE_FAILED"
    VERIFY_FAILED = "VERIFY_FAILED"
    CANCELLED_BY_USER = "CANCELLED_BY_USER"
    MEDIA_NOT_FOUND = "MEDIA_NOT_FOUND"
    MANIFEST_INVALID = "MANIFEST_INVALID"
    IPC_FAILED = "IPC_FAILED"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AutoSilentTrimmerException(Exception):
    """Base exception carrying a stable error code and localization hint key."""

    default_code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        hint_key: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or self.default_code
        self.hint_key = hint_key or f"error.{self.code.value.lower()}"
        self.context = context or {}


class MediaProcessingException(AutoSilentTrimmerException):
    """Exception raised during media probing, extraction, trimming, or muxing."""

    default_code = ErrorCode.CHUNK_FAILED


class FormatMismatchException(MediaProcessingException):
    """Exception raised when media container formats are incompatible or unsupported."""

    default_code = ErrorCode.UNSUPPORTED_FORMAT


class MediaFileNotFoundException(MediaProcessingException):
    """Exception raised when an input media file does not exist."""

    default_code = ErrorCode.MEDIA_NOT_FOUND


class FFmpegExecutionException(MediaProcessingException):
    """Exception raised when FFmpeg fails during execution."""

    default_code = ErrorCode.CHUNK_FAILED


class ChunkProcessingException(MediaProcessingException):
    """Exception raised when chunk processing exceeds retry limits."""

    default_code = ErrorCode.CHUNK_FAILED


class MergeException(MediaProcessingException):
    """Exception raised during chunk merging."""

    default_code = ErrorCode.MERGE_FAILED


class MediaVerificationException(MediaProcessingException):
    """Exception raised when post-merge verification detects stream/duration corruption."""

    default_code = ErrorCode.VERIFY_FAILED


class DiskFullException(MediaProcessingException):
    """Exception raised when destination volume lacks required temporary/output space."""

    default_code = ErrorCode.DISK_FULL


class SourceLockedException(MediaProcessingException):
    """Exception raised when a source file changes or locks mid-processing."""

    default_code = ErrorCode.SOURCE_LOCKED


class JobCancelledException(AutoSilentTrimmerException):
    """Exception raised when an active job is cancelled by user action."""

    default_code = ErrorCode.CANCELLED_BY_USER


class VoiceActivityDetectionException(MediaProcessingException):
    """Exception raised during VAD analysis."""

    default_code = ErrorCode.CHUNK_FAILED


class NoiseReductionException(MediaProcessingException):
    """Exception raised during noise reduction processing."""

    default_code = ErrorCode.CHUNK_FAILED


class ComputeBackendException(AutoSilentTrimmerException):
    """Exception raised when no suitable compute backend satisfies active policy."""

    default_code = ErrorCode.NO_COMPUTE_BACKEND


class DependencyMissingException(AutoSilentTrimmerException):
    """Exception raised when a required third-party dependency is missing."""

    default_code = ErrorCode.DEPENDENCY_MISSING


class RuntimePackException(AutoSilentTrimmerException):
    """Exception raised during Runtime Pack manifest, download, or signature checks."""

    default_code = ErrorCode.RUNTIME_MISSING


class ManifestValidationException(RuntimePackException):
    """Exception raised when release manifest or cryptographic signature fails checks."""

    default_code = ErrorCode.MANIFEST_INVALID


class IPCException(AutoSilentTrimmerException):
    """Exception raised during single-instance gateway IPC communication."""

    default_code = ErrorCode.IPC_FAILED
