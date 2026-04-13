"""
Listens for Windows session lock / unlock events by registering a
message-only window for WTS session notifications.

All Win32 calls are made via ctypes to avoid a hard dependency on pywin32
at runtime (pywin32 is only needed for building).
"""
import ctypes
import ctypes.wintypes

from PyQt6.QtCore import QThread, pyqtSignal

# ------------------------------------------------------------------ #
# Win32 constants
# ------------------------------------------------------------------ #
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0
HWND_MESSAGE = ctypes.wintypes.HWND(-3)

# ------------------------------------------------------------------ #
# Win32 structures & function types
# ------------------------------------------------------------------ #
_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.wintypes.HWND,
    ctypes.c_uint,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize",        ctypes.c_uint),
        ("style",         ctypes.c_uint),
        ("lpfnWndProc",   _WNDPROC),
        ("cbClsExtra",    ctypes.c_int),
        ("cbWndExtra",    ctypes.c_int),
        ("hInstance",     ctypes.wintypes.HANDLE),
        ("hIcon",         ctypes.wintypes.HANDLE),
        ("hCursor",       ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HANDLE),
        ("lpszMenuName",  ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ("hIconSm",       ctypes.wintypes.HANDLE),
    ]


class SessionMonitor(QThread):
    locked = pyqtSignal()
    unlocked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Keep a reference so the WNDPROC is not garbage-collected while
        # the message loop runs.
        self._wndproc_ref = None

    def run(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        wtsapi32 = ctypes.windll.wtsapi32

        user32.CreateWindowExW.restype = ctypes.wintypes.HWND
        user32.DefWindowProcW.restype = ctypes.c_long

        def _wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_WTSSESSION_CHANGE:
                if wparam == WTS_SESSION_LOCK:
                    self.locked.emit()
                elif wparam == WTS_SESSION_UNLOCK:
                    self.unlocked.emit()
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = _WNDPROC(_wndproc)

        class_name = "PigmatoSessionMonitor"
        hinstance = kernel32.GetModuleHandleW(None)

        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinstance
        wc.lpszClassName = class_name

        user32.RegisterClassExW(ctypes.byref(wc))

        hwnd = user32.CreateWindowExW(
            0, class_name, None, 0,
            0, 0, 0, 0,
            HWND_MESSAGE, None, hinstance, None,
        )

        if not hwnd:
            return

        wtsapi32.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        wtsapi32.WTSUnRegisterSessionNotification(hwnd)
