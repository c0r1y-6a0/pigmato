from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from timer import PomodoroTimer, State
from storage import Storage

_STYLE = """
QWidget {
    background: #2C3E50;
    color: #ECF0F1;
    border-radius: 6px;
}
QLabel#status {
    font-size: 12px;
    color: #BDC3C7;
}
QComboBox {
    background: #34495E;
    border: 1px solid #4A6278;
    border-radius: 4px;
    padding: 6px 8px;
    color: #ECF0F1;
    font-size: 13px;
    min-width: 220px;
}
QComboBox:disabled { color: #7F8C8D; }
QComboBox QAbstractItemView {
    background: #34495E;
    color: #ECF0F1;
    selection-background-color: #2980B9;
}
QPushButton#start {
    background: #E74C3C;
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
    font-size: 13px;
    color: white;
}
QPushButton#start:hover { background: #C0392B; }
QPushButton#stop {
    background: #7F8C8D;
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
    font-size: 13px;
    color: white;
}
QPushButton#stop:hover { background: #636E72; }
"""


class PopupWindow(QWidget):
    def __init__(self, timer: PomodoroTimer, storage: Storage, parent=None):
        # Qt.WindowType.Popup auto-hides on click-outside
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup,
        )
        self._timer = timer
        self._storage = storage
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self._status_label = QLabel()
        self._status_label.setObjectName("status")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.lineEdit().setPlaceholderText("本次番茄主题…")
        layout.addWidget(self._combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._start_btn = QPushButton("开始")
        self._start_btn.setObjectName("start")
        self._start_btn.clicked.connect(self._on_start)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.setObjectName("stop")
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._on_stop)

        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)

        self.setStyleSheet(_STYLE)

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        """Sync UI state with the timer before showing."""
        state = self._timer.state
        topics = self._storage.config.recent_topics

        self._combo.clear()
        self._combo.addItems(topics)
        self._combo.setCurrentText("")

        if state == State.RUNNING:
            m, s = divmod(self._timer.remaining, 60)
            self._status_label.setText(f"进行中：{self._timer.topic}  {m:02d}:{s:02d}")
            self._status_label.setVisible(True)
            self._combo.setEnabled(False)
            self._start_btn.setVisible(False)
            self._stop_btn.setVisible(True)

        elif state == State.BREAK:
            m, s = divmod(self._timer.remaining, 60)
            self._status_label.setText(f"休息中  {m:02d}:{s:02d}")
            self._status_label.setVisible(True)
            self._combo.setEnabled(True)
            self._start_btn.setText("开始新番茄")
            self._start_btn.setVisible(True)
            self._stop_btn.setVisible(False)

        else:
            self._status_label.setVisible(False)
            self._combo.setEnabled(True)
            self._start_btn.setText("开始")
            self._start_btn.setVisible(True)
            self._stop_btn.setVisible(False)

        self.adjustSize()

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        topic = self._combo.currentText().strip()
        if not topic:
            self._combo.lineEdit().setPlaceholderText("请先输入主题！")
            self._combo.lineEdit().setFocus()
            return
        self._storage.add_topic(topic)
        self._timer.start_work(topic)
        self.hide()

    def _on_stop(self) -> None:
        self._timer.stop()
        self.hide()

    # ------------------------------------------------------------------ #
    # Keyboard shortcuts
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_start()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
