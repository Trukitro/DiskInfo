"""User-configurable options, persisted to a JSON file in %LOCALAPPDATA%\\DiskInfo."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def get_config_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    path = Path(base) / "DiskInfo"
    path.mkdir(parents=True, exist_ok=True)
    return path


SETTINGS_PATH = get_config_dir() / "settings.json"


@dataclass
class Settings:
    poll_interval_s: float = 5.0
    low_space_pct: float = 90.0
    notifications_enabled: bool = True
    port: int = 8745


def load_settings(path: Path = SETTINGS_PATH) -> Settings:
    defaults = Settings()
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return defaults
    merged = {**asdict(defaults), **data}
    return Settings(**{k: merged[k] for k in asdict(defaults)})


def save_settings(settings: Settings, path: Path = SETTINGS_PATH) -> None:
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
