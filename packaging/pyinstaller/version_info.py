# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Shared PyInstaller Windows VSVersionInfo builder sourcing branding SSOT."""

from __future__ import annotations

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from autosilenttrimmer.branding import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    COPYRIGHT_NOTICE,
)


def _version_tuple(version_str: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in version_str.split(".") if p.isdigit()]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # type: ignore[return-value]


def build_windows_version_info(
    *,
    original_filename: str,
    internal_name: str,
    file_description: str | None = None,
):
    """Build PyInstaller VSVersionInfo populating Windows File Properties -> Details."""
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )

    ver_tuple = _version_tuple(APP_VERSION)
    desc = file_description or f"{APP_NAME} — {APP_DESCRIPTION}"
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=ver_tuple,
            prodvers=ver_tuple,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", AUTHOR),
                            StringStruct("FileDescription", desc),
                            StringStruct("FileVersion", APP_VERSION),
                            StringStruct("InternalName", internal_name),
                            StringStruct("LegalCopyright", COPYRIGHT_NOTICE),
                            StringStruct("OriginalFilename", original_filename),
                            StringStruct("ProductName", APP_NAME),
                            StringStruct("ProductVersion", APP_VERSION),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
