# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Windows HKCU per-user File Explorer right-click shell integration (Doc 01 §9)."""

from __future__ import annotations

import logging
import os

from autosilenttrimmer.core.constants import SHELL_REGISTRY_MENU_KEY
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration

logger = logging.getLogger(__name__)


class WindowsRegistryShellAdapter(IShellIntegration):
    """Registers 'Trim This Video' on HKCU SystemFileAssociations without admin rights."""

    _BASE_ASSOC = r"Software\Classes\SystemFileAssociations"

    def register(self, executable_path: str, label: str, extensions: frozenset[str]) -> None:
        """Write clean per-user context menu registry entries for target media extensions."""
        import winreg

        abs_exe = os.path.abspath(executable_path)
        command_str = f'"{abs_exe}" --enqueue "%1"'

        for ext in sorted(extensions):
            norm_ext = ext if ext.startswith(".") else f".{ext}"
            verb_key_path = f"{self._BASE_ASSOC}\\{norm_ext}\\shell\\{SHELL_REGISTRY_MENU_KEY}"
            cmd_key_path = f"{verb_key_path}\\command"

            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, verb_key_path, 0, winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, abs_exe)
                winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")

            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, cmd_key_path, 0, winreg.KEY_WRITE
            ) as ckey:
                winreg.SetValueEx(ckey, "", 0, winreg.REG_SZ, command_str)

        logger.info("Registered Windows context menu for %d extensions.", len(extensions))

    def unregister(self, extensions: frozenset[str]) -> None:
        """Remove registered shell entries cleanly leaving zero orphaned verbs."""
        import winreg

        for ext in sorted(extensions):
            norm_ext = ext if ext.startswith(".") else f".{ext}"
            verb_key_path = f"{self._BASE_ASSOC}\\{norm_ext}\\shell\\{SHELL_REGISTRY_MENU_KEY}"
            cmd_key_path = f"{verb_key_path}\\command"
            self._delete_key_if_exists(winreg.HKEY_CURRENT_USER, cmd_key_path)
            self._delete_key_if_exists(winreg.HKEY_CURRENT_USER, verb_key_path)

        logger.info("Unregistered Windows context menu entries cleanly.")

    def is_registered(self, extensions: frozenset[str]) -> bool:
        """Verify at least Tier-1 primary entry (.mp4 or first extension) is present."""
        import winreg

        check_ext = ".mp4" if ".mp4" in extensions else next(iter(extensions), ".mp4")
        verb_key_path = (
            f"{self._BASE_ASSOC}\\{check_ext}\\shell\\{SHELL_REGISTRY_MENU_KEY}\\command"
        )
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, verb_key_path, 0, winreg.KEY_READ):
                return True
        except OSError:
            return False

    @staticmethod
    def _delete_key_if_exists(root_hive: int, sub_key: str) -> None:
        import winreg

        try:
            winreg.DeleteKey(root_hive, sub_key)
        except FileNotFoundError:
            return
        except OSError as exc:
            logger.debug("Skipping registry cleanup for %s: %s", sub_key, exc)
