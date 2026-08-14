"""Native Windows toast notifications via winotify, for drives approaching
full and predicted SMART failures. Falls back to a console line when
winotify or its Windows dependency isn't available (e.g. running tests on
non-Windows)."""

from __future__ import annotations

from .paths import ICON_PATH


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

    def _send(self, title: str, message: str) -> None:
        if self._Notification is None:
            print(f"[notify] {title}: {message}")
            return
        try:
            icon = str(ICON_PATH) if ICON_PATH.exists() else ""
            toast = self._Notification(app_id="DiskInfo", title=title, msg=message, icon=icon)
            toast.show()
        except Exception as exc:
            print(f"[notify:fallback] {title}: {message} ({exc})")
