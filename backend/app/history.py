"""Benchmark run history, persisted to a small SQLite database in
%LOCALAPPDATA%\\DiskInfo (same config dir settings.py uses) so past results
survive across app restarts instead of vanishing after each run."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .settings import get_config_dir

DB_PATH = get_config_dir() / "history.db"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive TEXT NOT NULL,
            ts REAL NOT NULL,
            write_avg_mb_s REAL NOT NULL,
            read_avg_mb_s REAL NOT NULL,
            total_mb INTEGER NOT NULL,
            cache_bypassed INTEGER NOT NULL
        )
        """
    )
    return conn


def record_run(
    drive: str,
    write_avg_mb_s: float,
    read_avg_mb_s: float,
    total_mb: int,
    cache_bypassed: bool,
    path: Path = DB_PATH,
) -> None:
    with _connect(path) as conn:
        conn.execute(
            "INSERT INTO benchmark_runs (drive, ts, write_avg_mb_s, read_avg_mb_s, total_mb, cache_bypassed) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (drive, time.time(), write_avg_mb_s, read_avg_mb_s, total_mb, int(cache_bypassed)),
        )


def get_history(drive: str | None = None, limit: int = 20, path: Path = DB_PATH) -> list[dict]:
    with _connect(path) as conn:
        conn.row_factory = sqlite3.Row
        if drive:
            rows = conn.execute(
                "SELECT * FROM benchmark_runs WHERE drive = ? ORDER BY ts DESC LIMIT ?", (drive, limit)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM benchmark_runs ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [
            {
                "id": row["id"],
                "drive": row["drive"],
                "ts": row["ts"],
                "write_avg_mb_s": row["write_avg_mb_s"],
                "read_avg_mb_s": row["read_avg_mb_s"],
                "total_mb": row["total_mb"],
                "cache_bypassed": bool(row["cache_bypassed"]),
            }
            for row in rows
        ]
