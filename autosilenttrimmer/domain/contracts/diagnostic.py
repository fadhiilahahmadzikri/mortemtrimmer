"""Contract for system diagnostics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from autosilenttrimmer.domain.models.readiness import ReadinessItem


class ISystemDiagnostic(ABC):
    """Abstract interface for a subsystem health diagnostic check."""

    @property
    @abstractmethod
    def category_name(self) -> str:
        """Name of the diagnostic category."""
        pass

    @abstractmethod
    def check(self) -> list[ReadinessItem]:
        """Perform diagnostic verification and return items."""
        pass
