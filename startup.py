import sys
import winreg

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "Pigmato"


def _exe_path() -> str:
    # When frozen by PyInstaller sys.executable is the .exe itself
    if getattr(sys, "frozen", False):
        return sys.executable
    # In dev, launch via Python interpreter
    return f'"{sys.executable}" "{sys.argv[0]}"'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except OSError:
        return False


def enable() -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _REG_KEY, access=winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_path())


def disable() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, access=winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _APP_NAME)
    except OSError:
        pass
