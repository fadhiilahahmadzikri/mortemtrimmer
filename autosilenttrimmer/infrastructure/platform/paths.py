"""Cross-platform directory resolution powered by platformdirs."""

from __future__ import annotations

import os

from autosilenttrimmer.core.constants import APP_SLUG
from autosilenttrimmer.domain.contracts.platform_paths import IPlatformPaths
from platformdirs import PlatformDirs


def normalize_os_path(path: str) -> str:
    """Resolve absolute path and apply Windows extended prefix for deep Unicode paths (Doc 01 §9)."""
    abs_path = os.path.abspath(path)
    if os.name == "nt" and len(abs_path) >= 240 and not abs_path.startswith("\\\\?\\"):
        if abs_path.startswith("\\\\"):
            return "\\\\?\\UNC\\" + abs_path.lstrip("\\")
        return "\\\\?\\" + abs_path
    return abs_path


class PlatformDirsPaths(IPlatformPaths):
    """OS-agnostic application storage directories (AppData / Application Support / XDG)."""

    def __init__(self, app_name: str = APP_SLUG, root_override: str | None = None) -> None:
        self._root_override = os.path.abspath(root_override) if root_override else None
        self._dirs = PlatformDirs(appname=app_name, appauthor=False)

    @property
    def data_dir(self) -> str:
        return self._root_override or self._dirs.user_data_dir

    @property
    def cache_dir(self) -> str:
        return (
            os.path.join(self._root_override, "cache")
            if self._root_override
            else self._dirs.user_cache_dir
        )

    @property
    def logs_dir(self) -> str:
        return (
            os.path.join(self._root_override, "logs")
            if self._root_override
            else self._dirs.user_log_dir
        )

    @property
    def runtime_packs_dir(self) -> str:
        return os.path.join(self.data_dir, "runtime_packs")

    @property
    def jobs_dir(self) -> str:
        return os.path.join(self.data_dir, "jobs")

    @property
    def settings_file(self) -> str:
        return os.path.join(self.data_dir, "settings.json")

    @property
    def capabilities_cache_file(self) -> str:
        return os.path.join(self.cache_dir, "capabilities_cache.json")

    def ensure_all_dirs(self) -> None:
        """Create all managed per-user application directories safely."""
        for folder in (
            self.data_dir,
            self.cache_dir,
            self.logs_dir,
            self.runtime_packs_dir,
            self.jobs_dir,
        ):
            os.makedirs(folder, exist_ok=True)
