# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-dir spec for Self-Contained Offline AutoSilentTrimmer Desktop Suite."""

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
for p in (SPECPATH, ROOT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from version_info import build_windows_version_info

INCLUDE_AI = os.environ.get("INCLUDE_AI_BUNDLE", "1") == "1"

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

DATAS = [
    (
        os.path.join(ROOT_DIR, "autosilenttrimmer", "presentation", "assets"),
        os.path.join("autosilenttrimmer", "presentation", "assets"),
    ),
    (os.path.join(ROOT_DIR, "LICENSE"), "."),
]
notices_file = os.path.join(ROOT_DIR, "packaging", "dist_notices", "THIRD_PARTY_NOTICES.txt")
if os.path.isfile(notices_file):
    DATAS.append((notices_file, "."))
BINARIES = []
APP_ICON = os.path.join(ROOT_DIR, "packaging", "windows", "mortem.ico")
HIDDENIMPORTS = [
    "pystray._win32",
    "desktop_notifier.backends.winrt",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
    "PyQt6.QtSvg",
]

if INCLUDE_AI:
    offline_models_dir = os.path.join(ROOT_DIR, "packaging", "offline_models")
    if os.path.isdir(offline_models_dir):
        DATAS.append((offline_models_dir, "offline_models"))

    DATAS.extend(collect_data_files("faster_whisper"))
    DATAS.extend(collect_data_files("noisereduce"))
    DATAS.extend(collect_data_files("scipy"))

    for pkg in ("ctranslate2", "df", "onnxruntime"):
        p_datas, p_bins, p_hidden = collect_all(pkg)
        DATAS.extend(p_datas)
        BINARIES.extend(p_bins)
        HIDDENIMPORTS.extend(p_hidden)

    HIDDENIMPORTS.extend(collect_submodules("scipy"))
    HIDDENIMPORTS.extend([
        "torch",
        "torchaudio",
        "faster_whisper",
        "noisereduce",
        "matplotlib",
        "seaborn",
        "tqdm",
    ])
else:
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
    binaries=BINARIES,
    datas=DATAS,
    hiddenimports=HIDDENIMPORTS,
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
    icon=APP_ICON,
    version=build_windows_version_info(
        original_filename="autosilenttrimmer.exe",
        internal_name="MortemTrimmer",
    ),
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
    icon=APP_ICON,
    version=build_windows_version_info(
        original_filename="autosilenttrimmer-cli.exe",
        internal_name="MortemTrimmerCLI",
    ),
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
