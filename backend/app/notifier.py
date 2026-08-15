"""Native Windows toast notifications via winotify, for drives approaching
full and predicted SMART failures. Falls back to a console line when
winotify or its Windows dependency isn't available (e.g. running tests on
non-Windows)."""

from __future__ import annotations

from .logging_setup import get_logger
from .paths import ICON_PATH

logger = get_logger("notifier")


class Notifier:
    def __init__(self) -> None:
        try:
            from winotify import Notification

            self._Notification = Notification
        except Exception:
            self._Notification = None

    def notify_low_space(self, mountpoint: str, percent: float) -> None:
        self._send("DiskInfo - Low disk space", f"{mountpoint} is {percent:.0f}% full.")

    def notify_predicted_failure(self, model: str, reason: str) -> None:
        self._send("DiskInfo - Drive health warning", f"{model}: predicted failure ({reason}).")

    def notify_high_temperature(self, model: str, temperature_c: int, threshold_c: int) -> None:
        self._send("DiskInfo - Drive temperature warning", f"{model} is at {temperature_c}°C (threshold {threshold_c}°C).")

    def _send(self, title: str, message: str) -> None:
        logger.info("%s: %s", title, message)
        if self._Notification is None:
            return
        try:
            icon = str(ICON_PATH) if ICON_PATH.exists() else ""
            toast = self._Notification(app_id="DiskInfo", title=title, msg=message, icon=icon)
            toast.show()
        except Exception:
            logger.exception("toast notification failed: %s: %s", title, message)
