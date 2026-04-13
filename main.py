import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from session_monitor import SessionMonitor
from storage import Storage
from timer import PomodoroTimer
from tray import TrayIcon


def main() -> None:
    app = QApplication(sys.argv)
    # Don't quit when all windows are closed — we live in the tray
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Pigmato")

    storage = Storage()
    timer = PomodoroTimer(storage)

    monitor = SessionMonitor()
    monitor.locked.connect(timer.on_manual_lock)
    monitor.unlocked.connect(timer.on_unlock)
    monitor.start()

    tray = TrayIcon(timer, storage, monitor)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_path = Path.home() / "pigmato_error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        raise
