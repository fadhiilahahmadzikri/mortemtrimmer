"""Declarative schema primitives for tunable application settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

TUNE_TABS: tuple[str, ...] = (
    "General & Pipeline",
    "VAD & Engines",
    "Encoder & Chunking",
    "Output & Paths",
    "System & Runtime",
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
    """Declarative metadata binding domain UserSettings to technical Tune UI controls."""

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
    special_zero_label: str | None = None


__all__ = ["TUNE_TABS", "ControlType", "SettingFieldSpec"]
