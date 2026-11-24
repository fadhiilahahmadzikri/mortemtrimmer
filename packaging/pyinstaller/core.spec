# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-dir spec for Lean Core AutoSilentTrimmer Windows Desktop Suite."""

import os

block_cipher = None
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
INCLUDE_AI = os.environ.get("INCLUDE_AI_BUNDLE", "0") == "1"

EXCLUDES = [
    "pytest",
    "ruff",
    "pre_commit",
    "commitizen",
    "setuptools",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtQuick",
    "PyQt6.QtQml",
    "PyQt6.Qt3DCore",
    "PyQt6.QtSql",
    "PyQt6.QtBluetooth",
    "PyQt6.QtPositioning",
    "PyQt6.QtPdf",
    "PyQt6.QtSensors",
    "PyQt6.QtSerialPort",
    "PyQt6.QtTest",
]
if not INCLUDE_AI:
    # Lean Core keeps heavy gigabyte ML wheels in on-demand Runtime Packs (Doc 02 §5.2-B)
    EXCLUDES.extend([
        "torch",
        "torchaudio",
        "faster_whisper",
        "ctranslate2",
        "df",
        "matplotlib",
        "seaborn",
        "scipy",
        "pandas",
        "noisereduce",
        "onnxruntime",
    ])

a = Analysis(
    [os.path.join(ROOT_DIR, "autosilenttrimmer", "__main__.py")],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pystray._win32",
        "desktop_notifier.backends.winrt",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtNetwork",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="autosilenttrimmer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

cli_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="autosilenttrimmer-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    cli_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="AutoSilentTrimmer",
)
