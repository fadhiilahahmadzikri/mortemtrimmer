"""Platform-agnostic directory resolution and long-path helper contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IPlatformPaths(ABC):
    """Resolves OS-standard per-user directories (Win AppData, macOS AppSupport, Linux XDG)."""

    @property
    @abstractmethod
    def data_dir(self) -> str:
        """Persistent app data directory."""
        pass

    @property
    @abstractmethod
    def cache_dir(self) -> str:
        """Volatile cache directory."""
        pass

    @property
    @abstractmethod
    def logs_dir(self) -> str:
        """Structured diagnostic log directory."""
        pass

    @property
    @abstractmethod
    def runtime_packs_dir(self) -> str:
        """Managed isolated runtime pack root directory."""
        pass

    @property
    @abstractmethod
    def jobs_dir(self) -> str:
        """Persistent job manifest state directory."""
        pass

    @property
    @abstractmethod
    def settings_file(self) -> str:
        """JSON user settings file path."""
        pass

    @property
    @abstractmethod
    def capabilities_cache_file(self) -> str:
        """Cached GPU/CPU capability probe file path."""
        pass

    @abstractmethod
    def ensure_all_dirs(self) -> None:
        """Ensure required application subdirectories exist."""
        pass
