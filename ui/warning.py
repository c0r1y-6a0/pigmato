from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from timer import State, PomodoroTimer

_STYLE = """
QWidget {
    background: #1E2A35;
    color: #ECF0F1;
    border-radius: 10px;
}
QLabel#title {
    font-size: 15px;
    font-weight: bold;
}
QLabel#countdown {
    font-size: 56px;
    font-weight: bold;
    color: #E67E22;
}
QPushButton {
    background: #E67E22;
    border: none;
    border-radius: 5px;
    padding: 8px 24px;
    font-size: 13px;
    color: white;
}
QPushButton:hover  { background: #D35400; }
QPushButton:disabled { background: #4A5568; color: #718096; }
"""


class WarningWindow(QWidget):
    def __init__(self, timer: PomodoroTimer, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool,
        )
        self._timer = timer
        self._setup_ui()
        self._center()

        timer.tick.connect(self._on_tick)
        timer.state_changed.connect(self._on_state_changed)

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 28, 40, 28)

        title = QLabel("番茄结束！即将锁屏")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._countdown = QLabel("30")
        self._countdown.setObjectName("countdown")
        self._countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._countdown)

        self._skip_btn = QPushButton("跳过本次锁屏")
        self._skip_btn.clicked.connect(self._skip)
        layout.addWidget(self._skip_btn)

        self.setStyleSheet(_STYLE)
        self.adjustSize()

    def _center(self) -> None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_tick(self, remaining: int) -> None:
        if self._timer.state != State.WARNING:
            return
        self._countdown.setText(str(max(remaining, 0)))
        if remaining <= 0:
            self._skip_btn.setEnabled(False)

    def _on_state_changed(self, state: State) -> None:
        if state != State.WARNING:
            self.hide()
            self.deleteLater()

    def _skip(self) -> None:
        self._timer.skip_lock_and_break()

    # ------------------------------------------------------------------ #
    # Prevent closing while WARNING is active
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        if self._timer.state == State.WARNING:
            event.ignore()
        else:
            event.accept()
