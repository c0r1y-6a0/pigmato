from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import startup
from session_monitor import SessionMonitor
from storage import Storage
from timer import PomodoroTimer, State
from ui.popup import PopupWindow
from ui.settings import SettingsDialog
from ui.warning import WarningWindow


# ------------------------------------------------------------------ #
# Icon generation
# ------------------------------------------------------------------ #

def _make_icon(hex_color: str, size: int = 64) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(hex_color))
    painter.setPen(Qt.PenStyle.NoPen)
    margin = size // 8
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.end()
    return QIcon(px)


_ICONS = {
    State.IDLE:    _make_icon("#888888"),
    State.RUNNING: _make_icon("#E74C3C"),
    State.WARNING: _make_icon("#E67E22"),
    State.BREAK:   _make_icon("#27AE60"),
}


# ------------------------------------------------------------------ #
# Tray icon
# ------------------------------------------------------------------ #

class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        timer: PomodoroTimer,
        storage: Storage,
        monitor: SessionMonitor,
        parent=None,
    ):
        super().__init__(_ICONS[State.IDLE], parent)
        self._timer = timer
        self._storage = storage
        self._popup: PopupWindow | None = None
        self._warning: WarningWindow | None = None

        # Timer signals
        timer.state_changed.connect(self._on_state_changed)
        timer.tick.connect(self._on_tick)
        timer.work_ended.connect(self._on_work_ended)
        timer.break_ended.connect(self._on_break_ended)

        # Session monitor signals
        monitor.unlocked.connect(self._on_unlock)

        # Tray activation
        self.activated.connect(self._on_activated)

        self.setToolTip("Pigmato — 空闲")
        self._rebuild_menu()

    # ------------------------------------------------------------------ #
    # Tray activation
    # ------------------------------------------------------------------ #

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_popup()

    def _toggle_popup(self) -> None:
        if self._popup is None:
            self._popup = PopupWindow(self._timer, self._storage)

        if self._popup.isVisible():
            self._popup.hide()
            return

        self._popup.refresh()
        self._position_popup()
        self._popup.show()
        self._popup.activateWindow()
        self._popup.setFocus()

    def _position_popup(self) -> None:
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor)
        if screen is None:
            screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        self._popup.adjustSize()
        pw = self._popup.width()
        ph = self._popup.height()
        # Appear just above the taskbar at the cursor's x position
        x = min(max(cursor.x() - pw // 2, avail.left()), avail.right() - pw)
        y = avail.bottom() - ph - 8
        self._popup.move(x, y)

    # ------------------------------------------------------------------ #
    # Timer slots
    # ------------------------------------------------------------------ #

    def _on_state_changed(self, state: State) -> None:
        self.setIcon(_ICONS[state])
        labels = {
            State.IDLE:    "空闲",
            State.RUNNING: f"进行中：{self._timer.topic}",
            State.WARNING: "即将锁屏！",
            State.BREAK:   "休息中",
        }
        self.setToolTip(f"Pigmato — {labels[state]}")
        self._rebuild_menu()

    def _on_tick(self, remaining: int) -> None:
        state = self._timer.state
        if state == State.RUNNING:
            m, s = divmod(remaining, 60)
            self.setToolTip(f"Pigmato — {self._timer.topic}  {m:02d}:{s:02d}")
        elif state == State.BREAK:
            m, s = divmod(remaining, 60)
            self.setToolTip(f"Pigmato — 休息中  {m:02d}:{s:02d}")

    def _on_work_ended(self) -> None:
        if self._popup:
            self._popup.hide()
        self._warning = WarningWindow(self._timer)
        self._warning.show()

    def _on_break_ended(self) -> None:
        self.showMessage(
            "Pigmato",
            "休息结束，开始新的番茄吧！",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    # ------------------------------------------------------------------ #
    # Session monitor slot
    # ------------------------------------------------------------------ #

    def _on_unlock(self) -> None:
        state = self._timer.state
        if state == State.BREAK:
            m, s = divmod(self._timer.remaining, 60)
            self.showMessage(
                "Pigmato",
                f"休息中，还剩 {m:02d}:{s:02d}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        elif state == State.IDLE:
            self.showMessage(
                "Pigmato",
                "可以开始新的番茄了！",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #

    def _rebuild_menu(self) -> None:
        menu = QMenu()
        state = self._timer.state

        # Status row (disabled, informational)
        if state == State.RUNNING:
            info = menu.addAction(f"  {self._timer.topic}")
            info.setEnabled(False)
            menu.addSeparator()
            menu.addAction("停止番茄", self._timer.stop)

        elif state == State.BREAK:
            info = menu.addAction("  休息中")
            info.setEnabled(False)
            menu.addSeparator()
            menu.addAction("跳过休息", self._timer.stop)

        elif state == State.WARNING:
            info = menu.addAction("  即将锁屏！")
            info.setEnabled(False)
            menu.addSeparator()

        else:
            info = menu.addAction("  空闲")
            info.setEnabled(False)
            menu.addSeparator()

        menu.addAction("设置…", self._open_settings)
        menu.addSeparator()

        exit_action = menu.addAction("退出")
        if state == State.WARNING:
            exit_action.setEnabled(False)
        else:
            exit_action.triggered.connect(self._quit)

        self.setContextMenu(menu)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _open_settings(self) -> None:
        dlg = SettingsDialog(
            self._storage,
            startup.is_enabled,
            startup.enable,
            startup.disable,
        )
        dlg.exec()

    @staticmethod
    def _quit() -> None:
        QApplication.quit()
