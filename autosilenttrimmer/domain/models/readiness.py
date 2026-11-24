# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Domain models and data structures for system readiness assessment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReadinessStatus(StrEnum):
    """Status indicating health or availability of a system component."""

    READY = "READY"
    AVAILABLE = "AVAILABLE"
    OPTIONAL_MISSING = "OPTIONAL_MISSING"
    WARNING = "WARNING"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ReadinessItem:
    """Individual diagnostic outcome for a system component."""

    component: str
    category: str
    status: ReadinessStatus
    detail: str
    is_critical: bool = True
    remediation: str | None = None


@dataclass(frozen=True)
class SystemReadinessReport:
    """Aggregated system diagnostic report."""

    items: list[ReadinessItem]
    is_ready: bool
    has_gpu_acceleration: bool
    summary: dict[str, int]
