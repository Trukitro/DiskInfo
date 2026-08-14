"""Windows autostart via the current user's Run registry key -- the same
key the installer's optional autostart checkbox writes to (see
installer/diskinfo.iss's [Registry] section), so toggling it here from the
Settings UI and toggling it at install time stay consistent with each
other rather than fighting over two different mechanisms."""

from __future__ import annotations

import sys
import winreg

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "DiskInfo"


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def enable() -> None:
    # Only meaningful for the packaged .exe -- in dev mode (`python
    # backend/run.py`) sys.executable is the Python interpreter itself,
    # which wouldn't relaunch DiskInfo. The Settings UI is expected to be
    # used against the installed app, same as the installer's own checkbox.
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, f'"{sys.executable}"')


def disable() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, _VALUE_NAME)
    except FileNotFoundError:
        pass
