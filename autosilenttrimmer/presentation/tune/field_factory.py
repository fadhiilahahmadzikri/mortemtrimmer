"""Schema-driven PyQt6 form widget factory for SettingFieldSpec descriptors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from autosilenttrimmer.core.settings_schema import ControlType, SettingFieldSpec


@dataclass(frozen=True)
class BoundFieldControl:
    """Adapter binding a SettingFieldSpec widget to uniform get/set value hooks."""

    spec: SettingFieldSpec
    widget: QWidget
    getter: Callable[[], Any]
    setter: Callable[[Any], None]


def build_field_control(
    spec: SettingFieldSpec,
    parent: QWidget,
    on_changed: Callable[[], None],
) -> BoundFieldControl:
    """Construct clean PyQt6 input control matching spec.control_type."""
    if spec.control_type == ControlType.BOOL:
        cb = QCheckBox(parent)
        cb.setToolTip(spec.description)
        cb.toggled.connect(lambda _checked: on_changed())
        return BoundFieldControl(
            spec=spec,
            widget=cb,
            getter=cb.isChecked,
            setter=lambda val: cb.setChecked(bool(val)),
        )

    if spec.control_type == ControlType.INT:
        spin = QSpinBox(parent)
        spin.setToolTip(spec.description)
        spin.setRange(
            int(spec.min_val) if spec.min_val is not None else -1_000_000,
            int(spec.max_val) if spec.max_val is not None else 1_000_000,
        )
        spin.setSingleStep(int(spec.step or 1))
        if spec.special_zero_label:
            spin.setSpecialValueText(spec.special_zero_label)
        spin.valueChanged.connect(lambda _v: on_changed())

        def _get_int() -> int | None:
            v = spin.value()
            if spec.key == "max_workers" and v == 0:
                return None
            return v

        def _set_int(val: Any) -> None:
            spin.setValue(0 if val is None else int(val))

        return BoundFieldControl(spec=spec, widget=spin, getter=_get_int, setter=_set_int)

    if spec.control_type == ControlType.FLOAT:
        dspin = QDoubleSpinBox(parent)
        dspin.setToolTip(spec.description)
        dspin.setDecimals(spec.decimals)
        dspin.setRange(
            float(spec.min_val) if spec.min_val is not None else -1_000_000.0,
            float(spec.max_val) if spec.max_val is not None else 1_000_000.0,
        )
        dspin.setSingleStep(float(spec.step or 0.1))
        dspin.valueChanged.connect(lambda _v: on_changed())
        return BoundFieldControl(
            spec=spec,
            widget=dspin,
            getter=lambda: round(dspin.value(), spec.decimals + 2),
            setter=lambda val: dspin.setValue(float(val if val is not None else spec.default)),
        )

    if spec.control_type == ControlType.CHOICE:
        combo = QComboBox(parent)
        combo.setToolTip(spec.description)
        for choice in spec.choices:
            combo.addItem(spec.display_for_choice(choice), choice)
        combo.currentIndexChanged.connect(lambda _idx: on_changed())

        def _set_choice(val: Any) -> None:
            txt = str(val) if val is not None else str(spec.default)
            idx = combo.findData(txt)
            if idx < 0:
                idx = combo.findText(txt)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        return BoundFieldControl(
            spec=spec,
            widget=combo,
            getter=lambda: str(combo.currentData() or combo.currentText()),
            setter=_set_choice,
        )

    if spec.control_type in {ControlType.PATH_DIR, ControlType.PATH_FILE}:
        container = QWidget(parent)
        container.setObjectName("fieldContainer")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        line = QLineEdit(container)
        line.setToolTip(spec.description)
        line.setPlaceholderText("Automatic (leave blank)")
        line.textChanged.connect(lambda _txt: on_changed())

        browse_btn = QPushButton("Browse...", container)
        clear_btn = QPushButton("Clear", container)

        def _browse() -> None:
            if spec.control_type == ControlType.PATH_DIR:
                chosen = QFileDialog.getExistingDirectory(container, spec.label, line.text())
            else:
                chosen, _ = QFileDialog.getOpenFileName(container, spec.label, line.text())
            if chosen:
                line.setText(chosen)

        browse_btn.clicked.connect(_browse)
        clear_btn.clicked.connect(line.clear)

        layout.addWidget(line, stretch=1)
        layout.addWidget(browse_btn)
        layout.addWidget(clear_btn)

        return BoundFieldControl(
            spec=spec,
            widget=container,
            getter=lambda: line.text().strip() or None,
            setter=lambda val: line.setText("" if not val else str(val)),
        )

    edit = QLineEdit(parent)
    edit.setToolTip(spec.description)
    edit.textChanged.connect(lambda _txt: on_changed())
    return BoundFieldControl(
        spec=spec,
        widget=edit,
        getter=edit.text,
        setter=lambda val: edit.setText("" if val is None else str(val)),
    )
