"""Lifecycle logging and early progress-event helpers for JobOrchestrator."""

from __future__ import annotations

import logging
import os

from autosilenttrimmer.domain.contracts.event_bus import IEventBus
from autosilenttrimmer.domain.contracts.notifier import INotifier
from autosilenttrimmer.domain.entities.job import Job, JobState
from autosilenttrimmer.domain.models.events import (
    JobCompleted,
    JobFailed,
    JobStateChanged,
    ProgressUpdated,
)

logger = logging.getLogger(__name__)

_EARLY_STAGE_LABELS: dict[JobState, str] = {
    JobState.PROBING: "PROBING",
    JobState.PLANNING: "ANALYZING",
    JobState.PAUSED: "PAUSED",
    JobState.MERGING: "MERGING",
    JobState.VERIFYING: "VERIFYING",
}


def publish_stage_transition(bus: IEventBus, job: Job, prev: JobState, target: JobState) -> None:
    """Emit structured transition log, JobStateChanged, and non-terminal progress pulse."""
    fname = os.path.basename(job.source_path)
    bus.publish(
        JobStateChanged(job_id=job.job_id, previous_state=prev.value, new_state=target.value)
    )
    logger.info("Job %s [%s -> %s] file=%s", job.job_id[:8], prev.value, target.value, fname)
    if target in _EARLY_STAGE_LABELS:
        bus.publish(
            ProgressUpdated(
                job_id=job.job_id,
                filename=fname,
                percent=job.progress_percent,
                backend_label=_EARLY_STAGE_LABELS[target],
            )
        )
    elif target == JobState.RUNNING:
        bus.publish(
            ProgressUpdated(
                job_id=job.job_id,
                filename=fname,
                percent=15.0,
                backend_label=job.backend_id.upper(),
            )
        )


def publish_job_completed(
    bus: IEventBus,
    notifier: INotifier | None,
    job: Job,
    final_output: str,
    original_dur: float,
    expected_dur: float,
    reduction_pct: float,
) -> None:
    """Log completion summary and publish completion event + OS/tray notification."""
    logger.info(
        "Job %s DONE %.2fs -> %.2fs (%.1f%% removed) -> %s",
        job.job_id[:8],
        original_dur,
        expected_dur,
        reduction_pct,
        final_output,
    )
    bus.publish(
        JobCompleted(
            job_id=job.job_id,
            source_path=job.source_path,
            output_path=final_output,
            original_duration=original_dur,
            final_duration=expected_dur,
            reduction_percentage=reduction_pct,
        )
    )
    if notifier:
        notifier.notify_completed(final_output, original_dur, expected_dur, reduction_pct)


def publish_job_failed(
    bus: IEventBus,
    notifier: INotifier | None,
    job: Job,
    error_code: str,
    msg: str,
) -> None:
    """Log failure persistently and notify subscribers + user visibly."""
    logger.error("Job %s FAILED [%s] file=%s: %s", job.job_id[:8], error_code, job.source_path, msg)
    bus.publish(
        JobFailed(
            job_id=job.job_id,
            source_path=job.source_path,
            error_code=error_code,
            message=msg,
        )
    )
    if notifier:
        notifier.notify_failed(job.source_path, error_code, msg)
