# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Anonymized diagnostics bundle export use case (Doc 01 §10, Doc 02 §5.10)."""

from __future__ import annotations

import getpass
import json
import os
import time
import zipfile
from dataclasses import asdict

from autosilenttrimmer.domain.contracts.compute import ICapabilityProber
from autosilenttrimmer.domain.contracts.platform_paths import IPlatformPaths
from autosilenttrimmer.domain.contracts.runtime_manager import IRuntimeManager
from autosilenttrimmer.domain.contracts.storage import ISettingsRepository


def _scrub_pii(text: str) -> str:
    """Redact host username from local path strings before exporting support archives."""
    try:
        user = getpass.getuser()
        if user and len(user) > 1:
            return text.replace(user, "<USER>")
    except Exception:
        pass
    return text


class ExportDiagnosticsUseCase:
    """Packages capability snapshots, installed pack state, and logs into an anonymized ZIP."""

    def __init__(
        self,
        paths: IPlatformPaths,
        capability_prober: ICapabilityProber,
        runtime_manager: IRuntimeManager,
        settings_repo: ISettingsRepository,
    ) -> None:
        self._paths = paths
        self._prober = capability_prober
        self._runtime_manager = runtime_manager
        self._settings_repo = settings_repo

    def execute(self, output_zip_path: str | None = None) -> str:
        """Create anonymized diagnostics archive and return absolute path."""
        self._paths.ensure_all_dirs()
        target = output_zip_path or os.path.join(
            self._paths.logs_dir,
            f"diagnostics_{int(time.time())}.zip",
        )
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)

        caps = self._prober.probe()
        packs = self._runtime_manager.list_installed()
        settings = self._settings_repo.load()

        snapshot = {
            "exported_at": time.time(),
            "capabilities": asdict(caps),
            "installed_packs": [asdict(p) for p in packs],
            "settings": settings.to_dict(),
        }
        snapshot_json = _scrub_pii(json.dumps(snapshot, indent=2))

        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("environment_snapshot.json", snapshot_json)
            if os.path.isdir(self._paths.logs_dir):
                for entry in sorted(os.listdir(self._paths.logs_dir)):
                    if not entry.endswith(".log"):
                        continue
                    full_path = os.path.join(self._paths.logs_dir, entry)
                    if os.path.isfile(full_path):
                        with open(full_path, encoding="utf-8", errors="ignore") as lf:
                            zf.writestr(f"logs/{entry}", _scrub_pii(lf.read()))

        return os.path.abspath(target)
