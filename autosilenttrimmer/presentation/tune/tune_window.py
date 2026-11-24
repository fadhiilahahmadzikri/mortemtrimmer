"""Minimal PyQt6 tabbed Tune inspector modeled on Docker Desktop settings."""

from __future__ import annotations

import os
import subprocess
import sys

from PyQt6.QtCore import Qt
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

from autosilenttrimmer.core.constants import APP_NAME, TIER1_VIDEO_EXTENSIONS, VIDEO_EXTENSIONS
from autosilenttrimmer.core.settings_schema import SETTINGS_SCHEMA, TUNE_TABS, SettingFieldSpec
from autosilenttrimmer.domain.contracts.ipc import IJobGatewayClient
from autosilenttrimmer.domain.contracts.shell_integration import IShellIntegration
from autosilenttrimmer.domain.contracts.storage import ISettingsRepository
from autosilenttrimmer.domain.models.settings import UserSettings
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
    """Technical configuration editor reading/persisting UserSettings to settings.json."""

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

        self.setWindowTitle(f"Tune — {APP_NAME}")
        self.resize(720, 580)
        self.setMinimumSize(620, 480)

        self._build_ui()
        self._load_into_widgets(self._repo.load())

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        # Header
        header_row = QHBoxLayout()
        title_lbl = QLabel(f"{APP_NAME} Configuration", self)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
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
        reset_btn = QPushButton("Reset Defaults", self)
        open_json_btn = QPushButton("Open settings.json", self)
        close_btn = QPushButton("Close", self)
        self._apply_btn = QPushButton("Apply && Save", self)
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
        page = QWidget(scroll)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        grouped: dict[str, list[SettingFieldSpec]] = {}
        for spec in SETTINGS_SCHEMA:
            if spec.tab == tab_name:
                grouped.setdefault(spec.group, []).append(spec)

        for group_name, specs in grouped.items():
            box = QGroupBox(group_name, page)
            form = QFormLayout(box)
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
        box = QGroupBox("Explorer Context Menu", parent)
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
            "Status: Registered ('Trim This Video')" if active else "Status: Not registered"
        )
        self._shell_toggle_btn.setText("Unregister Menu" if active else "Register Menu")

    def _on_toggle_shell(self) -> None:
        if self._shell is None:
            return
        exts = TIER1_VIDEO_EXTENSIONS | VIDEO_EXTENSIONS
        if self._shell.is_registered(TIER1_VIDEO_EXTENSIONS):
            self._shell.unregister(exts)
        else:
            self._shell.register(self._shim_exe, APP_NAME, exts)
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
        self._set_dirty(True, "Modified (unsaved)")

    def _set_dirty(self, dirty: bool, message: str) -> None:
        self._dirty = dirty
        self._status_lbl.setText(message)
        color = "#ffca28" if dirty else "#00e676"
        self._status_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _on_reset_defaults(self) -> None:
        self._load_into_widgets(UserSettings())
        self._set_dirty(True, "Defaults loaded (click Apply & Save)")

    def _on_open_settings_file(self) -> None:
        if not os.path.isfile(self._settings_file):
            self._repo.save(self._collect_settings())
        _open_file_in_os(self._settings_file)

    def _on_apply_save(self) -> None:
        updated = self._collect_settings()
        self._repo.save(updated)
        notified = bool(self._gateway and self._gateway.notify_settings_updated())
        status = "Saved & hot-reloaded in active daemon" if notified else "Saved to settings.json"
        self._set_dirty(False, status)
