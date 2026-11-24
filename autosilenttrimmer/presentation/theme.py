"""Canonical Mortem Primer visual tokens, QSS theme, icon loader, and UI formatters."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Obsidian, Burnished Gold & Warm Brown palette derived from Mortem Primer emblem
BG_DEEP = "#14100E"
BG_BASE = "#1C1613"
BG_SURFACE = "#261E18"
BG_ELEVATED = "#33271F"
BG_HOVER = "#423226"
BG_PRESSED = "#2B2018"

BORDER_SUBTLE = "#453324"
BORDER_STRONG = "#8C5A2B"

TEXT_PRIMARY = "#F4EAD5"
TEXT_SECONDARY = "#B9A07E"
TEXT_ON_ACCENT = "#17110C"

ACCENT_GOLD = "#D99A2B"
ACCENT_GOLD_BRIGHT = "#F3C05B"
ACCENT_GOLD_MUTED = "#4D3718"

STATUS_OK = "#EAB34B"
STATUS_WARN = "#E58335"
STATUS_ERROR = "#E05A47"
STATUS_ERROR_BG = "#361B17"
STATUS_ERROR_TEXT = "#F49A8E"

PALETTE_WINDOW_RGB = (28, 22, 19)
PALETTE_WINDOW_TEXT_RGB = (244, 234, 213)
PALETTE_BASE_RGB = (20, 16, 14)
PALETTE_ALT_BASE_RGB = (38, 30, 24)
PALETTE_BUTTON_RGB = (51, 39, 31)
PALETTE_HIGHLIGHT_RGB = (217, 154, 43)
PALETTE_HIGHLIGHT_TEXT_RGB = (23, 17, 12)

_STAGE_DISPLAY_LABELS: dict[str, str] = {
    "QUEUED": "Queued",
    "STARTING": "Starting",
    "PROBING": "Inspecting Media",
    "ANALYZING": "Analyzing Speech",
    "PAUSED": "Paused",
    "MERGING": "Merging Segments",
    "VERIFYING": "Verifying Output",
    "CPU": "CPU",
}

_ERROR_DISPLAY_LABELS: dict[str, str] = {
    "UNSUPPORTED_FORMAT": "Unsupported Media Format",
    "NO_COMPUTE_BACKEND": "No Compute Backend Available",
    "RUNTIME_MISSING": "Runtime Component Missing",
    "DISK_FULL": "Insufficient Disk Space",
    "SOURCE_LOCKED": "Source File Locked",
    "CHUNK_FAILED": "Segment Processing Failed",
    "MERGE_FAILED": "Media Merge Failed",
    "VERIFY_FAILED": "Output Verification Failed",
    "CANCELLED_BY_USER": "Cancelled",
    "MEDIA_NOT_FOUND": "Source File Not Found",
    "MANIFEST_INVALID": "Manifest Check Failed",
    "IPC_FAILED": "Service Connection Failed",
    "DEPENDENCY_MISSING": "Dependency Missing",
    "INTERNAL_ERROR": "Unexpected Error",
}


def resolve_asset_path(filename: str) -> str | None:
    """Resolve bundled presentation image asset in both development and frozen builds."""
    rel = Path("autosilenttrimmer") / "presentation" / "assets" / filename
    candidates = [Path(__file__).resolve().parent / "assets" / filename]
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / rel)
        exe_dir = Path(os.path.dirname(os.path.abspath(sys.executable)))
        candidates.insert(1, exe_dir / rel)
        candidates.insert(2, exe_dir / "_internal" / rel)
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def format_stage_label(raw_stage: str) -> str:
    """Convert internal pipeline stage or backend identifier into clean user-facing text."""
    token = raw_stage.strip().upper()
    if token in _STAGE_DISPLAY_LABELS:
        return _STAGE_DISPLAY_LABELS[token]
    if token.startswith("GPU-"):
        return f"GPU ({token[4:]})"
    cleaned = re.sub(r"[_-]+", " ", raw_stage).strip()
    return cleaned.title() if cleaned else "Processing"


def format_error_code_label(raw_code: str) -> str:
    """Format canonical internal error codes cleanly without underscores for UI surfaces."""
    token = raw_code.strip().upper()
    if not token:
        return "Processing Failed"
    if token.startswith("E_"):
        token = token[2:]
    if token in _ERROR_DISPLAY_LABELS:
        return _ERROR_DISPLAY_LABELS[token]
    cleaned = re.sub(r"[_-]+", " ", token).strip()
    return cleaned.title() if cleaned else "Processing Failed"


def build_qt_stylesheet() -> str:
    """Construct cohesive gold-and-warm-brown QSS stylesheet across PyQt6 surfaces."""
    check_svg = resolve_asset_path("check_dark.svg")
    chevron_down_svg = resolve_asset_path("chevron_gold.svg")
    chevron_up_svg = resolve_asset_path("chevron_up_gold.svg")
    check_rule = f'image: url("{Path(check_svg).as_posix()}");' if check_svg is not None else ""
    chevron_down_rule = (
        f'image: url("{Path(chevron_down_svg).as_posix()}"); width: 10px; height: 10px;'
        if chevron_down_svg is not None
        else ""
    )
    chevron_up_rule = (
        f'image: url("{Path(chevron_up_svg).as_posix()}"); width: 10px; height: 10px;'
        if chevron_up_svg is not None
        else ""
    )

    return f"""
    QMainWindow, QDialog {{
        background-color: {BG_BASE};
        color: {TEXT_PRIMARY};
        font-family: "Segoe UI";
        font-size: 9.5pt;
    }}
    QWidget#centralRoot {{
        background-color: {BG_BASE};
        color: {TEXT_PRIMARY};
        font-family: "Segoe UI";
        font-size: 9.5pt;
    }}
    QWidget#scrollPage, QWidget#fieldContainer {{
        background-color: transparent;
    }}
    QLabel {{
        background-color: transparent;
        color: {TEXT_PRIMARY};
    }}
    QLabel#headerTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
    }}
    QLabel#headerSubtitle {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        background-color: {BG_BASE};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {BG_DEEP};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 7px 12px;
        margin-right: 4px;
        font-weight: 500;
    }}
    QTabBar::tab:hover {{
        background-color: {BG_SURFACE};
        color: {TEXT_PRIMARY};
    }}
    QTabBar::tab:selected {{
        background-color: {BG_BASE};
        color: {ACCENT_GOLD_BRIGHT};
        border-color: {BORDER_STRONG};
        border-top: 2px solid {ACCENT_GOLD};
        font-weight: 600;
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QGroupBox {{
        background-color: {BG_SURFACE};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 7px;
        margin-top: 14px;
        padding: 16px 14px 12px 14px;
        font-weight: 600;
        color: {ACCENT_GOLD_BRIGHT};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 1px 6px;
        background-color: {BG_BASE};
        color: {ACCENT_GOLD_BRIGHT};
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {BG_DEEP};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 5px;
        padding: 5px 10px;
        min-height: 20px;
        selection-background-color: {ACCENT_GOLD_MUTED};
        selection-color: {TEXT_PRIMARY};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {ACCENT_GOLD};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border: none;
    }}
    QComboBox::down-arrow {{
        {chevron_down_rule}
    }}
    QSpinBox, QDoubleSpinBox {{
        min-width: 110px;
        padding-right: 24px;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {BORDER_SUBTLE};
        border-top-right-radius: 5px;
        background-color: {BG_ELEVATED};
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border-left: 1px solid {BORDER_SUBTLE};
        border-bottom-right-radius: 5px;
        background-color: {BG_ELEVATED};
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {BG_HOVER};
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        {chevron_up_rule}
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        {chevron_down_rule}
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_DEEP};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_STRONG};
        selection-background-color: {ACCENT_GOLD};
        selection-color: {TEXT_ON_ACCENT};
        outline: 0;
        padding: 4px;
    }}
    QCheckBox {{
        background-color: transparent;
        spacing: 8px;
        color: {TEXT_PRIMARY};
    }}
    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
        border-radius: 4px;
        border: 1px solid {BORDER_STRONG};
        background-color: {BG_DEEP};
    }}
    QCheckBox::indicator:hover {{
        border-color: {ACCENT_GOLD_BRIGHT};
    }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT_GOLD};
        border-color: {ACCENT_GOLD_BRIGHT};
        {check_rule}
    }}
    QPlainTextEdit {{
        background-color: {BG_DEEP};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        padding: 8px;
        selection-background-color: {ACCENT_GOLD_MUTED};
        selection-color: {TEXT_PRIMARY};
    }}
    QPushButton {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 5px;
        padding: 6px 14px;
        min-height: 20px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {BG_HOVER};
        border-color: {BORDER_STRONG};
    }}
    QPushButton:pressed {{
        background-color: {BG_PRESSED};
    }}
    QPushButton#primaryButton {{
        background-color: {ACCENT_GOLD};
        color: {TEXT_ON_ACCENT};
        border: 1px solid {ACCENT_GOLD_BRIGHT};
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {ACCENT_GOLD_BRIGHT};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {BORDER_STRONG};
        color: {TEXT_PRIMARY};
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background-color: {BG_DEEP};
        width: 10px;
        height: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background-color: {BORDER_SUBTLE};
        border-radius: 5px;
        min-height: 24px;
        min-width: 24px;
    }}
    QScrollBar::handle:hover {{
        background-color: {BORDER_STRONG};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    QToolTip {{
        background-color: {BG_SURFACE};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_STRONG};
        padding: 5px 8px;
        border-radius: 4px;
    }}
    """
