import ctypes
from datetime import datetime
from enum import Enum, auto

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from storage import Storage

WARNING_SECONDS = 30


class State(Enum):
    IDLE = auto()
    RUNNING = auto()
    WARNING = auto()   # 30-second pre-lock countdown
    BREAK = auto()


class PomodoroTimer(QObject):
    state_changed = pyqtSignal(State)
    tick = pyqtSignal(int)          # remaining seconds in current phase
    work_ended = pyqtSignal()       # triggers the warning window
    break_ended = pyqtSignal()      # break finished, back to IDLE

    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._state = State.IDLE
        self._topic = ""
        self._remaining = 0
        self._cycle_count = 0
        self._start_time: datetime | None = None

        self._qtimer = QTimer(self)
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._on_tick)

    # ------------------------------------------------------------------ #
    # Public read-only properties
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> State:
        return self._state

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def remaining(self) -> int:
        return self._remaining

    # ------------------------------------------------------------------ #
    # Public actions
    # ------------------------------------------------------------------ #

    def start_work(self, topic: str) -> None:
        """Start a new Pomodoro, stopping whatever is running."""
        self._qtimer.stop()
        self._topic = topic.strip()
        self._start_time = datetime.now()
        self._remaining = self._storage.config.work_minutes * 60
        self._set_state(State.RUNNING)
        self._qtimer.start()

    def stop(self) -> None:
        """Manually cancel the current Pomodoro or break (not logged)."""
        self._qtimer.stop()
        self._start_time = None
        self._set_state(State.IDLE)

    def skip_lock_and_break(self) -> None:
        """User pressed 'skip' in the warning window — log session, skip lock, start break."""
        self._qtimer.stop()
        self._log_session()
        self._start_break()

    # ------------------------------------------------------------------ #
    # Session monitor callbacks
    # ------------------------------------------------------------------ #

    def on_manual_lock(self) -> None:
        """User manually locked the screen — treat as Pomodoro end."""
        if self._state in (State.RUNNING, State.WARNING):
            self._qtimer.stop()
            self._log_session()
            self._cycle_count += 1
            # Screen is already locked; skip the lock step, go straight to break
            self._start_break()
        elif self._state == State.BREAK:
            self._qtimer.stop()
            self._set_state(State.IDLE)

    def on_unlock(self) -> None:
        """Propagated to UI layer via tray; no timer logic needed here."""

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _log_session(self) -> None:
        if self._start_time is not None:
            self._storage.log_session(self._topic, self._start_time, datetime.now())
            self._start_time = None

    def _start_break(self) -> None:
        cfg = self._storage.config
        if self._cycle_count % cfg.cycles_before_long_break == 0:
            self._remaining = cfg.long_break_minutes * 60
        else:
            self._remaining = cfg.short_break_minutes * 60
        self._set_state(State.BREAK)
        self._qtimer.start()

    def _on_tick(self) -> None:
        self._remaining -= 1
        self.tick.emit(self._remaining)

        if self._state == State.RUNNING and self._remaining <= 0:
            self._qtimer.stop()
            self._remaining = WARNING_SECONDS
            self._set_state(State.WARNING)
            self._qtimer.start()
            self.work_ended.emit()

        elif self._state == State.WARNING and self._remaining <= 0:
            self._qtimer.stop()
            self._log_session()
            self._cycle_count += 1
            ctypes.windll.user32.LockWorkStation()
            self._start_break()

        elif self._state == State.BREAK and self._remaining <= 0:
            self._qtimer.stop()
            self._set_state(State.IDLE)
            self.break_ended.emit()

    def _set_state(self, state: State) -> None:
        self._state = state
        self.state_changed.emit(state)
