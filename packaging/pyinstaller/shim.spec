# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ultra-fast thin Explorer shell handler (trim-shim.exe <100ms)."""

import os
import sys

block_cipher = None
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
for p in (SPECPATH, ROOT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from version_info import build_windows_version_info

SHIM_DATAS = [
    (
        os.path.join(ROOT_DIR, "autosilenttrimmer", "presentation", "assets", "github_mark.svg"),
        os.path.join("autosilenttrimmer", "presentation", "assets"),
    ),
    (
        os.path.join(ROOT_DIR, "autosilenttrimmer", "presentation", "assets", "mortem_icon.png"),
        os.path.join("autosilenttrimmer", "presentation", "assets"),
    ),
    (os.path.join(ROOT_DIR, "LICENSE"), "."),
]
notices_file = os.path.join(ROOT_DIR, "packaging", "dist_notices", "THIRD_PARTY_NOTICES.txt")
if os.path.isfile(notices_file):
    SHIM_DATAS.append((notices_file, "."))

a = Analysis(
    [os.path.join(ROOT_DIR, "scripts", "shell_shim.py")],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=SHIM_DATAS,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchaudio",
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "seaborn",
        "PIL",
        "cv2",
        "av",
        "df",
        "faster_whisper",
        "onnxruntime",
        "tkinter",
        "pystray",
        "PyQt6",
        "PySide6",
        "cryptography",
        "httpx",
        "pytest",
        "ruff",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="trim-shim",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=os.path.join(ROOT_DIR, "packaging", "windows", "mortem.ico"),
    version=build_windows_version_info(
        original_filename="trim-shim.exe",
        internal_name="MortemTrimShim",
        file_description="Mortem Primer Explorer Context Menu Launcher",
    ),
)
