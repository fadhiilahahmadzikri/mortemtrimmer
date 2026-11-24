# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Cross-platform process priority and battery awareness via psutil."""

from __future__ import annotations

import logging
import os

import psutil
from autosilenttrimmer.core.constants import DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT
from autosilenttrimmer.domain.contracts.compute import IProcessPriorityController

logger = logging.getLogger(__name__)


class PsutilPriorityController(IProcessPriorityController):
    """Applies low CPU/IO priority for polite background execution (Doc 01 §7.5)."""

    def __init__(
        self,
        low_battery_threshold_percent: float = DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT,
    ) -> None:
        self._low_battery_threshold = low_battery_threshold_percent

    def apply_background_priority(self) -> None:
        """Set background priority cleanly across Windows, macOS, and Linux."""
        try:
            proc = psutil.Process(os.getpid())
            if os.name == "nt":
                proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                if hasattr(psutil, "IOPRIO_LOW"):
                    proc.ionice(psutil.IOPRIO_LOW)
            else:
                proc.nice(10)
        except Exception as exc:
            logger.debug("Could not adjust process priority cleanly: %s", exc)

    def is_low_battery(self) -> bool:
        """Check battery level when running unplugged."""
        try:
            battery = psutil.sensors_battery()
            if battery is None or battery.power_plugged:
                return False
            return float(battery.percent) <= self._low_battery_threshold
        except Exception:
            return False
