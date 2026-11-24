# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Persistent storage contracts for user settings and crash-resumable job manifests."""

from __future__ import annotations

from abc import ABC, abstractmethod

from autosilenttrimmer.domain.entities.job import Job
from autosilenttrimmer.domain.models.settings import UserSettings


class ISettingsRepository(ABC):
    """Stores and retrieves UserSettings atomically."""

    @abstractmethod
    def load(self) -> UserSettings:
        """Load persisted UserSettings or default settings if absent."""
        pass

    @abstractmethod
    def save(self, settings: UserSettings) -> None:
        """Atomically persist UserSettings to disk."""
        pass


class IJobManifestRepository(ABC):
    """Persists job state and completed chunk manifests for resume and diagnostics."""

    @abstractmethod
    def save_job(self, job: Job) -> None:
        """Persist current job & chunk state atomically."""
        pass

    @abstractmethod
    def load_job(self, job_id: str) -> Job | None:
        """Load job state manifest by job_id if present."""
        pass

    @abstractmethod
    def list_resumable_jobs(self) -> list[Job]:
        """Return unfinished non-terminal jobs available for crash recovery."""
        pass

    @abstractmethod
    def delete_job(self, job_id: str) -> None:
        """Remove job manifest after completion/cleanup if desired."""
        pass
