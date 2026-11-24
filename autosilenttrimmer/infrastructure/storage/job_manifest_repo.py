# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Atomic JSON job manifest persistence for pause & crash recovery."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

from autosilenttrimmer.domain.contracts.storage import IJobManifestRepository
from autosilenttrimmer.domain.entities.job import ChunkStatus, ChunkTask, Job, JobState
from autosilenttrimmer.domain.entities.segment import MediaSegment


class JsonJobManifestRepository(IJobManifestRepository):
    """Persists Job aggregate and ChunkTask completion manifests atomically."""

    def __init__(self, jobs_dir: str) -> None:
        self._jobs_dir = jobs_dir
        os.makedirs(self._jobs_dir, exist_ok=True)

    def _manifest_path(self, job_id: str) -> str:
        return os.path.join(self._jobs_dir, f"{job_id}.json")

    def save_job(self, job: Job) -> None:
        """Serialize Job state machine and chunks atomically."""
        os.makedirs(self._jobs_dir, exist_ok=True)
        target = self._manifest_path(job.job_id)
        tmp = f"{target}.tmp"
        payload = self._serialize_job(job)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, target)

    def load_job(self, job_id: str) -> Job | None:
        """Deserialize Job manifest if present and valid."""
        target = self._manifest_path(job_id)
        if not os.path.isfile(target):
            return None
        try:
            with open(target, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize_job(data)
        except (OSError, KeyError, TypeError, ValueError):
            return None

    def list_resumable_jobs(self) -> list[Job]:
        """List non-terminal persisted jobs available for recovery."""
        resumable: list[Job] = []
        if not os.path.isdir(self._jobs_dir):
            return resumable
        for entry in sorted(os.listdir(self._jobs_dir)):
            if not entry.endswith(".json"):
                continue
            job_id = entry[:-5]
            job = self.load_job(job_id)
            if job is not None and not job.is_terminal:
                resumable.append(job)
        return resumable

    def delete_job(self, job_id: str) -> None:
        """Delete job manifest cleanly if it exists."""
        target = self._manifest_path(job_id)
        if os.path.isfile(target):
            os.remove(target)

    @staticmethod
    def _serialize_job(job: Job) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "source_path": job.source_path,
            "output_path": job.output_path,
            "strategy": job.strategy,
            "state": job.state.value,
            "total_duration": job.total_duration,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "backend_id": job.backend_id,
            "source_size": job.source_size,
            "source_mtime": job.source_mtime,
            "chunks": [
                {
                    "index": c.index,
                    "start_sec": c.start_sec,
                    "end_sec": c.end_sec,
                    "output_path": c.output_path,
                    "status": c.status.value,
                    "retries": c.retries,
                    "error_message": c.error_message,
                    "segments": [asdict(s) for s in c.segments],
                }
                for c in job.chunks
            ],
        }

    @staticmethod
    def _deserialize_job(data: dict[str, Any]) -> Job:
        chunks = [
            ChunkTask(
                index=c["index"],
                start_sec=c["start_sec"],
                end_sec=c["end_sec"],
                segments=[MediaSegment(start=s["start"], end=s["end"]) for s in c["segments"]],
                output_path=c.get("output_path"),
                status=ChunkStatus(c.get("status", ChunkStatus.PENDING.value)),
                retries=c.get("retries", 0),
                error_message=c.get("error_message"),
            )
            for c in data.get("chunks", [])
        ]
        return Job(
            job_id=data["job_id"],
            source_path=data["source_path"],
            output_path=data.get("output_path"),
            strategy=data.get("strategy", "auto-silence"),
            state=JobState(data.get("state", JobState.QUEUED.value)),
            chunks=chunks,
            total_duration=data.get("total_duration", 0.0),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            backend_id=data.get("backend_id", "cpu"),
            source_size=data.get("source_size", 0),
            source_mtime=data.get("source_mtime", 0.0),
        )
