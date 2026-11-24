"""Domain events emitted by Orchestrator, WorkerPool, and RuntimeManager."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainEvent:
    """Base event record pushed over IEventBus."""

    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class JobQueued(DomainEvent):
    """Emitted when one or more sources enter the orchestrator queue."""

    job_id: str = ""
    source_path: str = ""


@dataclass(frozen=True)
class JobStarted(DomainEvent):
    """Emitted when a job begins probing."""

    job_id: str = ""
    source_path: str = ""


@dataclass(frozen=True)
class JobStateChanged(DomainEvent):
    """Emitted on every state machine transition."""

    job_id: str = ""
    previous_state: str = ""
    new_state: str = ""


@dataclass(frozen=True)
class ChunkCompleted(DomainEvent):
    """Emitted when a parallel chunk finishes encoding or analysis."""

    job_id: str = ""
    chunk_index: int = 0
    total_chunks: int = 0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class ProgressUpdated(DomainEvent):
    """Emitted as weighted job completion and smoothed ETA update."""

    job_id: str = ""
    filename: str = ""
    percent: float = 0.0
    eta_seconds: float | None = None
    backend_label: str = "CPU"


@dataclass(frozen=True)
class BackendFallback(DomainEvent):
    """Emitted when GPU execution degrades gracefully to CPU under Policy G2."""

    job_id: str = ""
    from_backend: str = ""
    to_backend: str = ""
    reason: str = ""


@dataclass(frozen=True)
class JobCompleted(DomainEvent):
    """Emitted after output verification and atomic publish succeed."""

    job_id: str = ""
    source_path: str = ""
    output_path: str = ""
    original_duration: float = 0.0
    final_duration: float = 0.0
    reduction_percentage: float = 0.0


@dataclass(frozen=True)
class JobFailed(DomainEvent):
    """Emitted when a job terminates cleanly with a stable ErrorCode."""

    job_id: str = ""
    source_path: str = ""
    error_code: str = ""
    message: str = ""


@dataclass(frozen=True)
class JobCancelled(DomainEvent):
    """Emitted when user cancellation cleans up a job."""

    job_id: str = ""
    source_path: str = ""


@dataclass(frozen=True)
class RuntimeDownloadProgress(DomainEvent):
    """Emitted by RuntimeManager during resumable pack download."""

    pack_id: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
