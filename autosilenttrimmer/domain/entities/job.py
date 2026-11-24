"""Job aggregate entity, finite state machine, and chunk progress tracking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from autosilenttrimmer.domain.entities.segment import MediaSegment


class JobState(StrEnum):
    """Canonical lifecycle states for media trimming jobs (Doc 01 §6.2)."""

    QUEUED = "QUEUED"
    PROBING = "PROBING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    MERGING = "MERGING"
    VERIFYING = "VERIFYING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES: frozenset[JobState] = frozenset(
    {JobState.DONE, JobState.FAILED, JobState.CANCELLED}
)

VALID_JOB_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.PROBING, JobState.FAILED, JobState.CANCELLED}),
    JobState.PROBING: frozenset({JobState.PLANNING, JobState.FAILED, JobState.CANCELLED}),
    JobState.PLANNING: frozenset(
        {JobState.RUNNING, JobState.MERGING, JobState.DONE, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.RUNNING: frozenset(
        {JobState.PAUSED, JobState.MERGING, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.PAUSED: frozenset({JobState.RUNNING, JobState.FAILED, JobState.CANCELLED}),
    JobState.MERGING: frozenset({JobState.VERIFYING, JobState.FAILED, JobState.CANCELLED}),
    JobState.VERIFYING: frozenset({JobState.DONE, JobState.FAILED, JobState.CANCELLED}),
    JobState.DONE: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}


class ChunkStatus(StrEnum):
    """Execution status of an individual chunk unit."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ChunkTask:
    """Mutable progress state for a single planned media chunk."""

    index: int
    start_sec: float
    end_sec: float
    segments: list[MediaSegment]
    output_path: str | None = None
    status: ChunkStatus = ChunkStatus.PENDING
    retries: int = 0
    error_message: str | None = None

    @property
    def duration(self) -> float:
        """Return total chunk source span in seconds."""
        return max(0.0, self.end_sec - self.start_sec)


@dataclass
class Job:
    """Aggregate root owning state machine transitions and duration-weighted progress."""

    source_path: str
    output_path: str | None = None
    strategy: str = "auto-silence"
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: JobState = JobState.QUEUED
    chunks: list[ChunkTask] = field(default_factory=list)
    total_duration: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    backend_id: str = "cpu"
    source_size: int = 0
    source_mtime: float = 0.0

    def transition_to(self, target: JobState) -> None:
        """Advance state machine while guarding invariants."""
        allowed = VALID_JOB_TRANSITIONS.get(self.state, frozenset())
        if target not in allowed:
            raise ValueError(f"Invalid job transition: {self.state.value} -> {target.value}")
        self.state = target

    @property
    def is_terminal(self) -> bool:
        """Check whether job reached DONE, FAILED, or CANCELLED."""
        return self.state in TERMINAL_STATES

    @property
    def progress_percent(self) -> float:
        """Compute duration-weighted progress across pipeline stages (Doc 01 §7.9)."""
        stage_weights = {
            JobState.QUEUED: 0.0,
            JobState.PROBING: 5.0,
            JobState.PLANNING: 12.0,
            JobState.MERGING: 90.0,
            JobState.VERIFYING: 96.0,
            JobState.DONE: 100.0,
        }
        if self.state in stage_weights:
            return stage_weights[self.state]

        if self.state in {JobState.RUNNING, JobState.PAUSED}:
            if not self.chunks:
                return 15.0
            total_span = sum(c.duration for c in self.chunks)
            if total_span <= 0.0:
                completed = sum(1 for c in self.chunks if c.status == ChunkStatus.COMPLETED)
                ratio = completed / len(self.chunks)
            else:
                completed_span = sum(
                    c.duration for c in self.chunks if c.status == ChunkStatus.COMPLETED
                )
                ratio = min(1.0, completed_span / total_span)
            return 15.0 + (ratio * 73.0)

        return 0.0
