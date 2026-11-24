# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Shared About dialog, Third-Party Notices viewer, Help menu, and GitHub corner helpers."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from autosilenttrimmer.branding import (
    APP_NAME,
    APP_SHORT_NAME,
    APP_VERSION,
    ATTRIBUTION_LINE,
    COPYRIGHT_NOTICE,
    GITHUB_HANDLE,
    GITHUB_URL,
    LICENSE_NAME,
)
from autosilenttrimmer.presentation.theme import (
    ACCENT_GOLD_BRIGHT,
    TEXT_SECONDARY,
    render_github_icon,
    resolve_asset_path,
    resolve_bundled_doc_path,
)


def open_github_repository() -> bool:
    """Open canonical GitHub repository URL via Qt desktop handler cleanly."""
    return QDesktopServices.openUrl(QUrl(GITHUB_URL))


class GitHubCornerButton(QToolButton):
    """Subtle theme-adaptive clickable GitHub Octicon icon button."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("githubCornerButton")
        self.setToolTip(GITHUB_HANDLE)
        self.setAccessibleName(GITHUB_HANDLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(28, 28)
        self.setIconSize(QSize(16, 16))
        self.clicked.connect(open_github_repository)
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        fg_color = self.palette().color(QPalette.ColorRole.WindowText)
        icon = render_github_icon(fg_color, size=16)
        assert isinstance(icon, QIcon)
        self.setIcon(icon)

    def changeEvent(self, event: QEvent | None) -> None:
        super().changeEvent(event)
        if event is not None and event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        }:
            self._refresh_icon()


class ThirdPartyNoticesDialog(QDialog):
    """Offline read-only viewer for bundled third-party licenses and notices."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Third-Party Notices — {APP_NAME}")
        self.resize(740, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        notices_path = resolve_bundled_doc_path("THIRD_PARTY_NOTICES.txt")
        header = QLabel(
            f"Bundled Third-Party Open-Source Notices ({notices_path or 'Not generated'})",
            self,
        )
        header.setWordWrap(True)
        header.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(header)

        viewer = QPlainTextEdit(self)
        viewer.setReadOnly(True)
        if notices_path is not None:
            viewer.setPlainText(Path(notices_path).read_text(encoding="utf-8", errors="replace"))
        else:
            viewer.setPlainText(
                "Third-party notices file (THIRD_PARTY_NOTICES.txt) has not been generated yet.\n"
                "Run `make notices` or package the distribution build."
            )
        layout.addWidget(viewer, stretch=1)

        btn_row = QHBoxLayout()
        if notices_path is not None:
            open_ext_btn = QPushButton("Open File Externally", self)
            open_ext_btn.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(notices_path))
            )
            btn_row.addWidget(open_ext_btn)
        btn_row.addStretch(1)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class AboutDialog(QDialog):
    """Product About dialog presenting icon, authorship, copyright, GitHub link, and notices."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(14)
        self.icon_label = QLabel(self)
        icon_path = resolve_asset_path("mortem_icon.png")
        if icon_path is not None:
            self.icon_label.setPixmap(
                QPixmap(icon_path).scaled(
                    56,
                    56,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        top.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(4)
        self.title_label = QLabel(f"{APP_NAME} ({APP_SHORT_NAME})", self)
        self.title_label.setObjectName("headerTitle")
        self.version_label = QLabel(f"Version {APP_VERSION}", self)
        self.version_label.setStyleSheet(f"color: {ACCENT_GOLD_BRIGHT}; font-weight: 600;")
        self.author_label = QLabel(ATTRIBUTION_LINE, self)
        self.author_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        meta_col.addWidget(self.title_label)
        meta_col.addWidget(self.version_label)
        meta_col.addWidget(self.author_label)
        top.addLayout(meta_col, stretch=1)
        root.addLayout(top)

        self.copyright_label = QLabel(COPYRIGHT_NOTICE, self)
        self.license_label = QLabel(f"License: {LICENSE_NAME}", self)
        self.license_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        root.addWidget(self.copyright_label)
        root.addWidget(self.license_label)

        self.github_btn = QPushButton(GITHUB_URL, self)
        self.github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.github_btn.setToolTip(GITHUB_HANDLE)
        self.github_btn.clicked.connect(open_github_repository)
        self._refresh_github_btn_icon()
        root.addWidget(self.github_btn)

        footer = QHBoxLayout()
        self.notices_btn = QPushButton("Third-Party Notices", self)
        self.notices_btn.clicked.connect(self._open_notices)
        close_btn = QPushButton("Close", self)
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(self.notices_btn)
        footer.addStretch(1)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _refresh_github_btn_icon(self) -> None:
        fg_color = self.palette().color(QPalette.ColorRole.WindowText)
        icon = render_github_icon(fg_color, size=16)
        assert isinstance(icon, QIcon)
        self.github_btn.setIcon(icon)

    def _open_notices(self) -> None:
        dlg = ThirdPartyNoticesDialog(self)
        dlg.exec()

    def changeEvent(self, event: QEvent | None) -> None:
        super().changeEvent(event)
        if event is not None and event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        }:
            self._refresh_github_btn_icon()


def install_help_menu(window: QMainWindow) -> None:
    """Attach standard Help -> About and GitHub Repository menu items onto a main window."""
    menu_bar = window.menuBar()
    assert menu_bar is not None
    help_menu = menu_bar.addMenu("Help")
    assert help_menu is not None
    about_action = help_menu.addAction("About")
    assert about_action is not None
    about_action.triggered.connect(lambda: AboutDialog(window).exec())

    github_action = help_menu.addAction("GitHub Repository")
    assert github_action is not None
    github_action.triggered.connect(open_github_repository)


def create_attribution_label(parent: QWidget | None = None) -> QLabel:
    """Create uniform subtle authorship footer/subtitle label sourcing branding SSOT."""
    lbl = QLabel(ATTRIBUTION_LINE, parent)
    lbl.setObjectName("headerSubtitle")
    lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
    return lbl
