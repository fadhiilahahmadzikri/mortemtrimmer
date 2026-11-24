"""Declarative Single Source of Truth schema describing all tunable application parameters."""

from __future__ import annotations

from autosilenttrimmer.core.schema import TUNE_TABS, ControlType, SettingFieldSpec
from autosilenttrimmer.core.schema.execution_fields import EXECUTION_FIELD_SPECS
from autosilenttrimmer.core.schema.pipeline_fields import PIPELINE_FIELD_SPECS

SETTINGS_SCHEMA: tuple[SettingFieldSpec, ...] = (
    *PIPELINE_FIELD_SPECS,
    *EXECUTION_FIELD_SPECS,
)

SETTINGS_BY_KEY: dict[str, SettingFieldSpec] = {spec.key: spec for spec in SETTINGS_SCHEMA}

__all__ = [
    "SETTINGS_BY_KEY",
    "SETTINGS_SCHEMA",
    "TUNE_TABS",
    "ControlType",
    "SettingFieldSpec",
]
