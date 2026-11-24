# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Output integrity verifier checking duration, streams, and multi-point decodability."""

from __future__ import annotations

import os

import av

from autosilenttrimmer.core.constants import VERIFY_DURATION_TOLERANCE_SEC
from autosilenttrimmer.domain.contracts.media_verifier import (
    IMediaVerifier,
    VerificationReport,
)


class PyAVMediaVerifier(IMediaVerifier):
    """Validates output artifact integrity prior to atomic publish (Doc 01 §7.7)."""

    def __init__(self, duration_tolerance_sec: float = VERIFY_DURATION_TOLERANCE_SEC) -> None:
        self._tolerance = duration_tolerance_sec

    def verify(
        self,
        output_path: str,
        expected_duration_sec: float,
        expected_has_video: bool,
        expected_audio_streams: int,
        splice_points_sec: list[float] | None = None,
    ) -> VerificationReport:
        """Inspect container duration, streams, and decode sample frames."""
        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            return VerificationReport(
                passed=False,
                actual_duration_sec=0.0,
                expected_duration_sec=expected_duration_sec,
                streams_matched=False,
                decode_samples_checked=0,
                failure_reason="Output artifact is missing or zero bytes.",
            )

        try:
            with av.open(output_path) as container:
                actual_duration = (
                    float(container.duration / av.time_base)
                    if container.duration is not None
                    else 0.0
                )
                has_video = len(container.streams.video) > 0
                audio_count = len(container.streams.audio)
                streams_ok = (not expected_has_video or has_video) and (
                    audio_count >= expected_audio_streams
                )

                if not streams_ok:
                    return VerificationReport(
                        passed=False,
                        actual_duration_sec=actual_duration,
                        expected_duration_sec=expected_duration_sec,
                        streams_matched=False,
                        decode_samples_checked=0,
                        failure_reason=(
                            f"Stream mismatch: expected video={expected_has_video}, "
                            f"audio>={expected_audio_streams}; got video={has_video}, "
                            f"audio={audio_count}"
                        ),
                    )

                if expected_duration_sec > 0.0:
                    delta = abs(actual_duration - expected_duration_sec)
                    # Tolerate tiny audio frame rounding overhead
                    allowed_delta = max(self._tolerance, expected_duration_sec * 0.05)
                    if delta > allowed_delta:
                        return VerificationReport(
                            passed=False,
                            actual_duration_sec=actual_duration,
                            expected_duration_sec=expected_duration_sec,
                            streams_matched=True,
                            decode_samples_checked=0,
                            failure_reason=(
                                f"Duration mismatch: expected {expected_duration_sec:.2f}s, "
                                f"got {actual_duration:.2f}s (delta {delta:.2f}s)"
                            ),
                        )

                samples = self._sample_decode_points(container, actual_duration, splice_points_sec)

                return VerificationReport(
                    passed=True,
                    actual_duration_sec=actual_duration,
                    expected_duration_sec=expected_duration_sec,
                    streams_matched=True,
                    decode_samples_checked=samples,
                )

        except av.AVError as exc:
            return VerificationReport(
                passed=False,
                actual_duration_sec=0.0,
                expected_duration_sec=expected_duration_sec,
                streams_matched=False,
                decode_samples_checked=0,
                failure_reason=f"Decode failure: {exc}",
            )

    @staticmethod
    def _sample_decode_points(
        container: av.container.InputContainer,
        duration_sec: float,
        splice_points_sec: list[float] | None,
    ) -> int:
        """Seek and decode 1 frame at start, mid, end, and splice boundaries."""
        points = [0.0]
        if duration_sec > 0.5:
            points.extend([duration_sec * 0.5, max(0.0, duration_sec - 0.25)])
        if splice_points_sec:
            points.extend(p for p in splice_points_sec if 0.0 < p < duration_sec)

        target_stream = (
            container.streams.video[0]
            if container.streams.video
            else (container.streams.audio[0] if container.streams.audio else None)
        )
        if target_stream is None:
            return 0

        checked = 0
        for sec in sorted(set(points)):
            offset = int(sec * av.time_base)
            container.seek(offset, any_frame=False, backward=True)
            for _frame in container.decode(target_stream):
                checked += 1
                break
        return checked
