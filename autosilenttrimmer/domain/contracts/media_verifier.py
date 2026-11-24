# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Media verifier contract validating output integrity prior to atomic publish."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationReport:
    """Result of output integrity verification."""

    passed: bool
    actual_duration_sec: float
    expected_duration_sec: float
    streams_matched: bool
    decode_samples_checked: int
    failure_reason: str | None = None


class IMediaVerifier(ABC):
    """Abstract interface verifying merged output duration, streams, and decodability."""

    @abstractmethod
    def verify(
        self,
        output_path: str,
        expected_duration_sec: float,
        expected_has_video: bool,
        expected_audio_streams: int,
        splice_points_sec: list[float] | None = None,
    ) -> VerificationReport:
        """Inspect output file integrity before promoting from temp staging."""
        pass
