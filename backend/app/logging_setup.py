"""Rotating file logging to %LOCALAPPDATA%\\DiskInfo\\diskinfo.log, so a bug
report has something concrete to attach beyond "it didn't work" (see the
README's Troubleshooting section) -- replaces the scattered print()s that
went nowhere once the app is packaged with console=False."""

from __future__ import annotations

import logging
import logging.handlers

from .settings import get_config_dir

LOG_PATH = get_config_dir() / "diskinfo.log"
LOGGER_NAME = "diskinfo"


def configure_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return  # already configured -- safe to call from multiple entry points
    handler = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
