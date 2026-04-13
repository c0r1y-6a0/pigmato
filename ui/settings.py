from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from storage import Storage

_STYLE = """
QDialog {
    background: #2C3E50;
    color: #ECF0F1;
}
QLabel { color: #ECF0F1; font-size: 13px; }
QSpinBox, QCheckBox {
    background: #34495E;
    color: #ECF0F1;
    border: 1px solid #4A6278;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 13px;
}
QDialogButtonBox QPushButton {
    background: #2980B9;
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
    color: white;
    font-size: 13px;
}
QDialogButtonBox QPushButton:hover { background: #1F618D; }
"""


class SettingsDialog(QDialog):
    def __init__(
        self,
        storage: Storage,
        is_autostart: Callable[[], bool],
        enable_autostart: Callable[[], None],
        disable_autostart: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint)
        self._storage = storage
        self._is_autostart = is_autostart
        self._enable_autostart = enable_autostart
        self._disable_autostart = disable_autostart
        self.setWindowTitle("设置 — Pigmato")
        self.setStyleSheet(_STYLE)
        self._setup_ui()

    def _setup_ui(self) -> None:
        cfg = self._storage.config
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(20)

        def spinbox(lo, hi, val, suffix=""):
            sb = QSpinBox()
            sb.setRange(lo, hi)
            sb.setValue(val)
            if suffix:
                sb.setSuffix(f" {suffix}")
            return sb

        self._work   = spinbox(1, 120, cfg.work_minutes, "分钟")
        self._short  = spinbox(1,  60, cfg.short_break_minutes, "分钟")
        self._long   = spinbox(1, 120, cfg.long_break_minutes, "分钟")
        self._cycles = spinbox(1,  10, cfg.cycles_before_long_break, "个")
        self._auto   = QCheckBox()
        self._auto.setChecked(self._is_autostart())

        form.addRow("工作时长",      self._work)
        form.addRow("短休息",        self._short)
        form.addRow("长休息",        self._long)
        form.addRow("几个后长休息",  self._cycles)
        form.addRow("开机自启动",    self._auto)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self) -> None:
        cfg = self._storage.config
        cfg.work_minutes               = self._work.value()
        cfg.short_break_minutes        = self._short.value()
        cfg.long_break_minutes         = self._long.value()
        cfg.cycles_before_long_break   = self._cycles.value()
        cfg.autostart                  = self._auto.isChecked()

        if cfg.autostart:
            self._enable_autostart()
        else:
            self._disable_autostart()

        self._storage.save()
        self.accept()
