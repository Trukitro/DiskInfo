"""Windows autostart via Task Scheduler, not the registry Run key.

DiskInfo's exe carries a requireAdministrator manifest (see diskinfo.spec's
uac_admin=True), and Windows does not reliably UAC-prompt -- or simply
fails silently -- for an elevation-manifested exe launched from
HKCU\\...\\Run at logon. A scheduled task with "run with highest
privileges" is the correct, Microsoft-documented way to auto-start
something that needs admin, so that's what this uses instead."""

from __future__ import annotations

import subprocess
import sys

_TASK_NAME = "DiskInfoAutostart"

# CREATE_NO_WINDOW: schtasks is a console tool; without this a console
# window would flash briefly every time Settings reads/writes autostart,
# since DiskInfo itself runs windowed (console=False in diskinfo.spec).
_NO_WINDOW = 0x08000000


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, creationflags=_NO_WINDOW)


def is_enabled() -> bool:
    result = _run(["schtasks", "/query", "/tn", _TASK_NAME])
    return result.returncode == 0


def enable() -> None:
    # Only meaningful for the packaged .exe -- in dev mode (`python
    # backend/run.py`) sys.executable is the Python interpreter itself,
    # which wouldn't relaunch DiskInfo. The Settings UI is expected to be
    # used against the installed app.
    result = _run(
        [
            "schtasks",
            "/create",
            "/tn",
            _TASK_NAME,
            "/tr",
            f'"{sys.executable}"',
            "/sc",
            "onlogon",
            "/rl",
            "highest",
            "/f",
        ]
    )
    if result.returncode != 0:
        raise OSError(f"schtasks /create failed: {result.stderr.strip() or result.stdout.strip()}")


def disable() -> None:
    result = _run(["schtasks", "/delete", "/tn", _TASK_NAME, "/f"])
    # Exit code 1 with "cannot find" is schtasks' way of saying "already gone" -- fine.
    if result.returncode != 0 and "cannot find" not in result.stderr.lower():
        raise OSError(f"schtasks /delete failed: {result.stderr.strip() or result.stdout.strip()}")
