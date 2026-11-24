"""Minimal PyQt6 tabbed settings inspector for Mortem Primer."""

from __future__ import annotations

import os
import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from autosilenttrimmer.core.constants import (
    APP_NAME,
    SHELL_CONTEXT_MENU_LABEL,
    TIER1_VIDEO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from autosilenttrimmer.core.settings_schema import SETTINGS_SCHEMA, TUNE_TABS, SettingFieldSpec
from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration
from autosilenttrimmer.domain.contracts.storage import ISettingsRepository
from autosilenttrimmer.domain.models.settings import UserSettings
from autosilenttrimmer.presentation.theme import STATUS_OK, STATUS_WARN, resolve_asset_path
from autosilenttrimmer.presentation.tune.field_factory import (
    BoundFieldControl,
    build_field_control,
)


def _open_file_in_os(path: str) -> None:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return
    if os.name == "nt":
        os.startfile(abs_path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", abs_path])
    else:
        subprocess.Popen(["xdg-open", abs_path])


class TuneWindow(QMainWindow):
    """Configuration window reading and persisting UserSettings cleanly."""

    def __init__(
        self,
        *,
        settings_repo: ISettingsRepository,
        settings_file_path: str,
        gateway_client: IJobGatewayClient | None = None,
        shell_integration: IShellIntegration | None = None,
        shim_executable_path: str | None = None,
    ) -> None:
        super().__init__()
        self._repo = settings_repo
        self._settings_file = settings_file_path
        self._gateway = gateway_client
        self._shell = shell_integration
        self._shim_exe = shim_executable_path or sys.executable

        self._controls: dict[str, BoundFieldControl] = {}
        self._dirty = False

        self.setWindowTitle(f"Settings — {APP_NAME}")
        self.resize(820, 640)
        self.setMinimumSize(720, 520)

        self._build_ui()
        self._load_into_widgets(self._repo.load())

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon_path = resolve_asset_path("mortem_icon.png")
        if icon_path is not None:
            emblem = QLabel(self)
            emblem.setPixmap(
                QPixmap(icon_path).scaled(
                    26,
                    26,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            header_row.addWidget(emblem)

        title_lbl = QLabel(f"{APP_NAME} Settings", self)
        title_lbl.setObjectName("headerTitle")
        self._status_lbl = QLabel("Synchronized", self)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_row.addWidget(title_lbl)
        header_row.addStretch(1)
        header_row.addWidget(self._status_lbl)
        root_layout.addLayout(header_row)

        # Tab container
        self._tabs = QTabWidget(self)
        for tab_name in TUNE_TABS:
            self._tabs.addTab(self._build_tab(tab_name), tab_name)
        root_layout.addWidget(self._tabs, stretch=1)

        # Footer action bar
        footer_row = QHBoxLayout()
        footer_row.setSpacing(8)
        reset_btn = QPushButton("Reset Defaults", self)
        open_json_btn = QPushButton("Open Config File", self)
        open_json_btn.setToolTip("Open the JSON configuration file on disk.")
        close_btn = QPushButton("Close", self)
        self._apply_btn = QPushButton("Save && Apply", self)
        self._apply_btn.setObjectName("primaryButton")
        self._apply_btn.setDefault(True)

        reset_btn.clicked.connect(self._on_reset_defaults)
        open_json_btn.clicked.connect(self._on_open_settings_file)
        close_btn.clicked.connect(self.close)
        self._apply_btn.clicked.connect(self._on_apply_save)

        footer_row.addWidget(reset_btn)
        footer_row.addWidget(open_json_btn)
        footer_row.addStretch(1)
        footer_row.addWidget(close_btn)
        footer_row.addWidget(self._apply_btn)
        root_layout.addLayout(footer_row)

    def _build_tab(self, tab_name: str) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        page = QWidget(scroll)
        page.setObjectName("scrollPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(12)

        grouped: dict[str, list[SettingFieldSpec]] = {}
        for spec in SETTINGS_SCHEMA:
            if spec.tab == tab_name:
                grouped.setdefault(spec.group, []).append(spec)

        for group_name, specs in grouped.items():
            box = QGroupBox(group_name, page)
            form = QFormLayout(box)
            form.setHorizontalSpacing(20)
            form.setVerticalSpacing(10)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            for spec in specs:
                ctrl = build_field_control(spec, box, self._mark_dirty)
                self._controls[spec.key] = ctrl
                lbl = QLabel(spec.label, box)
                lbl.setToolTip(spec.description)
                form.addRow(lbl, ctrl.widget)
            page_layout.addWidget(box)

        if tab_name == TUNE_TABS[0] and self._shell is not None:
            page_layout.addWidget(self._build_shell_box(page))

        page_layout.addStretch(1)
        scroll.setWidget(page)
        return scroll

    def _build_shell_box(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Windows Explorer Context Menu", parent)
        row = QHBoxLayout(box)
        self._shell_status_lbl = QLabel(box)
        self._shell_toggle_btn = QPushButton(box)
        self._shell_toggle_btn.clicked.connect(self._on_toggle_shell)
        row.addWidget(self._shell_status_lbl)
        row.addStretch(1)
        row.addWidget(self._shell_toggle_btn)
        self._refresh_shell_status()
        return box

    def _refresh_shell_status(self) -> None:
        if self._shell is None:
            return
        active = self._shell.is_registered(TIER1_VIDEO_EXTENSIONS)
        self._shell_status_lbl.setText(
            f"Status: Active ('{SHELL_CONTEXT_MENU_LABEL}')" if active else "Status: Disabled"
        )
        self._shell_toggle_btn.setText("Remove Menu" if active else "Enable Menu")

    def _on_toggle_shell(self) -> None:
        if self._shell is None:
            return
        exts = TIER1_VIDEO_EXTENSIONS | VIDEO_EXTENSIONS
        if self._shell.is_registered(TIER1_VIDEO_EXTENSIONS):
            self._shell.unregister(exts)
        else:
            self._shell.register(self._shim_exe, SHELL_CONTEXT_MENU_LABEL, exts)
        self._refresh_shell_status()

    def _load_into_widgets(self, settings: UserSettings) -> None:
        data = settings.to_dict()
        for key, ctrl in self._controls.items():
            ctrl.widget.blockSignals(True)
            ctrl.setter(data.get(key))
            ctrl.widget.blockSignals(False)
        self._set_dirty(False, "Synchronized")

    def _collect_settings(self) -> UserSettings:
        draft = {key: ctrl.getter() for key, ctrl in self._controls.items()}
        return UserSettings.from_dict(draft)

    def _mark_dirty(self) -> None:
        self._set_dirty(True, "Unsaved changes")

    def _set_dirty(self, dirty: bool, message: str) -> None:
        self._dirty = dirty
        self._status_lbl.setText(message)
        color = STATUS_WARN if dirty else STATUS_OK
        self._status_lbl.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _on_reset_defaults(self) -> None:
        self._load_into_widgets(UserSettings())
        self._set_dirty(True, "Defaults loaded (save to apply)")

    def _on_open_settings_file(self) -> None:
        if not os.path.isfile(self._settings_file):
            self._repo.save(self._collect_settings())
        _open_file_in_os(self._settings_file)

    def _on_apply_save(self) -> None:
        updated = self._collect_settings()
        self._repo.save(updated)
        notified = bool(self._gateway and self._gateway.notify_settings_updated())
        status = "Saved & applied to active service" if notified else "Settings saved"
        self._set_dirty(False, status)
