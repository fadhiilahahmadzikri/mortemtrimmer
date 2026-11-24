# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Declarative schema primitives for tunable application settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

TUNE_TABS: tuple[str, ...] = (
    "General",
    "Speech and Audio",
    "Encoding and Speed",
    "Files and Output",
    "System and Updates",
)


class ControlType(StrEnum):
    """Framework-neutral UI control hints consumed cleanly by Tune presentation."""

    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    CHOICE = "choice"
    PATH_DIR = "path_dir"
    PATH_FILE = "path_file"


@dataclass(frozen=True)
class SettingFieldSpec:
    """Declarative metadata binding domain UserSettings to clean UI controls."""

    key: str
    tab: str
    group: str
    label: str
    description: str
    control_type: ControlType
    default: Any
    min_val: float | int | None = None
    max_val: float | int | None = None
    step: float | int | None = None
    decimals: int = 2
    choices: tuple[str, ...] = ()
    choice_labels: tuple[tuple[str, str], ...] = ()
    special_zero_label: str | None = None

    def display_for_choice(self, value: str) -> str:
        """Return polished user-facing label for a persisted choice value."""
        mapping = dict(self.choice_labels)
        return mapping.get(value, value.replace("_", " ").replace("-", " ").title())


__all__ = ["TUNE_TABS", "ControlType", "SettingFieldSpec"]
