"""Persistent user application settings domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from autosilenttrimmer.core.constants import (
    DEFAULT_COMPUTE_POLICY,
    DEFAULT_LANGUAGE,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_ON_CONFLICT,
    DEFAULT_OUTPUT_LOCATION,
    DEFAULT_OUTPUT_NAMING_TEMPLATE,
    DEFAULT_RELEASE_CHANNEL,
    DEFAULT_TRIM_STRATEGY,
    DEFAULT_VAD_METHOD,
)


@dataclass(frozen=True)
class UserSettings:
    """User-configurable preferences stored in platform data directory."""

    language: str = DEFAULT_LANGUAGE
    trim_strategy: str = DEFAULT_TRIM_STRATEGY
    vad_engine: str = DEFAULT_VAD_METHOD
    noise_reduction_method: str = DEFAULT_NOISE_REDUCTION_METHOD
    compute_policy: str = DEFAULT_COMPUTE_POLICY
    max_workers: int | None = None
    output_location: str = DEFAULT_OUTPUT_LOCATION
    output_custom_dir: str | None = None
    output_naming_template: str = DEFAULT_OUTPUT_NAMING_TEMPLATE
    on_conflict: str = DEFAULT_ON_CONFLICT
    pause_on_low_battery: bool = True
    background_priority: bool = True
    enable_notifications: bool = True
    generate_visual_artifacts: bool = False
    update_channel: str = DEFAULT_RELEASE_CHANNEL

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserSettings:
        """Deserialize settings ignoring unknown keys cleanly."""
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
