"""System tray icon: shows DiskInfo is running in the background and offers
Open/Exit. Closing the main window hides it (see shell.py); the tray icon
is the only way to actually end the process."""

from __future__ import annotations

import threading
from typing import Callable

import pystray
from PIL import Image

from .paths import ICON_PATH


def _load_icon_image() -> Image.Image:
    if ICON_PATH.exists():
        return Image.open(ICON_PATH)
    # Never let a missing icon asset silently mean "no tray icon at all".
    return Image.new("RGBA", (32, 32), (18, 179, 168, 255))


class TrayIcon:
    def __init__(self, on_open: Callable[[], None], on_exit: Callable[[], None]) -> None:
        self._icon = pystray.Icon(
            "DiskInfo",
            icon=_load_icon_image(),
            title="DiskInfo - running",
            menu=pystray.Menu(
                pystray.MenuItem("Open DiskInfo", lambda: on_open(), default=True),
                pystray.MenuItem("Exit", lambda: on_exit()),
            ),
        )

    def run_detached(self) -> None:
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self) -> None:
        self._icon.stop()
