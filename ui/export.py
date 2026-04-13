from collections import defaultdict
from datetime import date, datetime

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from storage import Session, Storage

_STYLE = """
QDialog {
    background: #2C3E50;
    color: #ECF0F1;
}
QLabel { color: #ECF0F1; font-size: 13px; }
QLabel#hint { color: #BDC3C7; font-size: 12px; }
QDateEdit {
    background: #34495E;
    color: #ECF0F1;
    border: 1px solid #4A6278;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 13px;
}
QDateEdit::drop-down { border: none; }
QDialogButtonBox QPushButton {
    background: #2980B9;
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
    color: white;
    font-size: 13px;
}
QDialogButtonBox QPushButton:hover { background: #1F618D; }
QDialogButtonBox QPushButton:disabled { background: #4A5568; color: #718096; }
"""


def _to_markdown(sessions: list[Session], start_date: date, end_date: date) -> str:
    lines = [
        "# Pigmato 番茄日志",
        "",
        f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"时间段：{start_date}  ~  {end_date}",
        "",
    ]

    by_date: dict[date, list[Session]] = defaultdict(list)
    for s in sessions:
        by_date[datetime.fromisoformat(s.start).date()].append(s)

    total = 0
    for d in sorted(by_date.keys(), reverse=True):
        day_sessions = sorted(by_date[d], key=lambda s: s.start)
        lines.append(f"## {d.strftime('%Y-%m-%d')}")
        lines.append("")
        for s in day_sessions:
            s_dt = datetime.fromisoformat(s.start)
            e_dt = datetime.fromisoformat(s.end)
            lines.append(f"- {s_dt.strftime('%H:%M')} ~ {e_dt.strftime('%H:%M')}　{s.topic}")
        lines.append("")
        lines.append(f"小计：{len(day_sessions)} 个番茄")
        lines.append("")
        total += len(day_sessions)

    lines += ["---", f"合计：{total} 个番茄", ""]
    return "\n".join(lines)


class ExportDialog(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint)
        self._storage = storage
        self.setWindowTitle("导出日志 — Pigmato")
        self.setStyleSheet(_STYLE)
        self._setup_ui()
        self._refresh_count()

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(20)

        today = QDate.currentDate()
        month_start = QDate(today.year(), today.month(), 1)

        self._start_edit = QDateEdit(month_start)
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("yyyy-MM-dd")
        self._start_edit.dateChanged.connect(self._on_date_changed)

        self._end_edit = QDateEdit(today)
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("yyyy-MM-dd")
        self._end_edit.dateChanged.connect(self._on_date_changed)

        form.addRow("开始日期", self._start_edit)
        form.addRow("结束日期", self._end_edit)
        root.addLayout(form)

        self._count_label = QLabel()
        self._count_label.setObjectName("hint")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._count_label)

        buttons = QDialogButtonBox()
        self._export_btn = buttons.addButton("导出…", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._export_btn.clicked.connect(self._export)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_date_changed(self) -> None:
        # Keep start <= end
        if self._start_edit.date() > self._end_edit.date():
            self.sender()  # identify which changed
            if self.sender() is self._start_edit:
                self._end_edit.setDate(self._start_edit.date())
            else:
                self._start_edit.setDate(self._end_edit.date())
        self._refresh_count()

    def _refresh_count(self) -> None:
        sessions = self._get_sessions()
        n = len(sessions)
        self._count_label.setText(f"该时间段内共 {n} 个番茄")
        self._export_btn.setEnabled(n > 0)

    def _export(self) -> None:
        sessions = self._get_sessions()
        if not sessions:
            return

        start = self._start_edit.date().toPyDate()
        end   = self._end_edit.date().toPyDate()

        default_name = f"pigmato_{start}_{end}.md"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 Markdown 文件",
            default_name,
            "Markdown 文件 (*.md);;所有文件 (*)",
        )
        if not path:
            return

        content = _to_markdown(sessions, start, end)
        try:
            from pathlib import Path
            Path(path).write_text(content, encoding="utf-8")
        except OSError as e:
            QMessageBox.warning(self, "导出失败", str(e))
            return

        self.accept()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_sessions(self) -> list[Session]:
        return self._storage.get_sessions(
            self._start_edit.date().toPyDate(),
            self._end_edit.date().toPyDate(),
        )
