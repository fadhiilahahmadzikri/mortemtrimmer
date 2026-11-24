# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ultra-fast thin Explorer shell handler (trim-shim.exe <100ms)."""

import os

block_cipher = None
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

a = Analysis(
    [os.path.join(ROOT_DIR, "scripts", "shell_shim.py")],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=[],
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
)
