"""Atomic JSON repository for persistent UserSettings."""

from __future__ import annotations

import json
import os

from autosilenttrimmer.domain.contracts.storage import ISettingsRepository
from autosilenttrimmer.domain.models.settings import UserSettings


class JsonSettingsRepository(ISettingsRepository):
    """Stores UserSettings atomically in platform config/data path."""

    def __init__(self, settings_path: str) -> None:
        self._settings_path = settings_path

    def load(self) -> UserSettings:
        """Read UserSettings or return defaults when missing/corrupt."""
        if not os.path.isfile(self._settings_path):
            return UserSettings()
        try:
            with open(self._settings_path, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                return UserSettings.from_dict(raw)
        except (OSError, ValueError):
            return UserSettings()
        return UserSettings()

    def save(self, settings: UserSettings) -> None:
        """Atomically persist UserSettings via temp file + os.replace."""
        parent = os.path.dirname(os.path.abspath(self._settings_path))
        os.makedirs(parent, exist_ok=True)
        tmp_path = f"{self._settings_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)
        os.replace(tmp_path, self._settings_path)
