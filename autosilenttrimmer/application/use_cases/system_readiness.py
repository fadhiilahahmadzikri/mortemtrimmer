"""System readiness use case: orchestrates subsystem health diagnostics."""

from __future__ import annotations

import logging
from collections import Counter

from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.models.readiness import (
    ReadinessItem,
    ReadinessStatus,
    SystemReadinessReport,
)

logger = logging.getLogger(__name__)


class SystemReadinessUseCase:
    """Use case to assess environment readiness and report health status."""

    def __init__(self, diagnostics: list[ISystemDiagnostic]) -> None:
        self._diagnostics = diagnostics

    def execute(self) -> SystemReadinessReport:
        """Run all registered diagnostics and compile an aggregate readiness report."""
        logger.info("Executing system readiness diagnostic audit...")
        all_items: list[ReadinessItem] = []

        for diagnostic in self._diagnostics:
            logger.debug("Checking category: %s", diagnostic.category_name)
            items = diagnostic.check()
            all_items.extend(items)

        status_counts = Counter(item.status.value for item in all_items)
        has_critical_failures = any(
            item.is_critical and item.status == ReadinessStatus.FAILED
            for item in all_items
        )
        is_ready = not has_critical_failures

        has_gpu_acceleration = any(
            item.component == "CUDA Hardware Acceleration"
            and item.status == ReadinessStatus.READY
            for item in all_items
        )

        return SystemReadinessReport(
            items=all_items,
            is_ready=is_ready,
            has_gpu_acceleration=has_gpu_acceleration,
            summary=dict(status_counts),
        )
