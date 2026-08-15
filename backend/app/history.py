"""Benchmark run history, persisted to a small SQLite database in
%LOCALAPPDATA%\\DiskInfo (same config dir settings.py uses) so past results
survive across app restarts instead of vanishing after each run."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .settings import get_config_dir

DB_PATH = get_config_dir() / "history.db"

# Columns added after the table's original 6.1.0 shape -- ALTERed in on
# open so a history.db from an earlier install keeps its existing rows
# instead of needing to be deleted.
_ADDED_COLUMNS = [
    ("iops_write", "REAL"),
    ("iops_read", "REAL"),
    ("avg_latency_write_ms", "REAL"),
    ("avg_latency_read_ms", "REAL"),
    ("underperforming", "INTEGER"),
    ("underperforming_reason", "TEXT"),
]


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
            cache_bypassed INTEGER NOT NULL,
            iops_write REAL,
            iops_read REAL,
            avg_latency_write_ms REAL,
            avg_latency_read_ms REAL,
            underperforming INTEGER,
            underperforming_reason TEXT
        )
        """
    )
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(benchmark_runs)")}
    for name, decl in _ADDED_COLUMNS:
        if name not in existing_cols:
            conn.execute(f"ALTER TABLE benchmark_runs ADD COLUMN {name} {decl}")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            ts REAL NOT NULL,
            temperature_c INTEGER,
            health_percentage INTEGER NOT NULL,
            predicted_failure INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_health_snapshots_device_ts ON health_snapshots (device_id, ts)")
    return conn


def record_run(
    drive: str,
    write_avg_mb_s: float,
    read_avg_mb_s: float,
    total_mb: int,
    cache_bypassed: bool,
    iops_write: float | None = None,
    iops_read: float | None = None,
    avg_latency_write_ms: float | None = None,
    avg_latency_read_ms: float | None = None,
    underperforming: bool | None = None,
    underperforming_reason: str | None = None,
    path: Path = DB_PATH,
) -> None:
    with _connect(path) as conn:
        conn.execute(
            "INSERT INTO benchmark_runs "
            "(drive, ts, write_avg_mb_s, read_avg_mb_s, total_mb, cache_bypassed, "
            "iops_write, iops_read, avg_latency_write_ms, avg_latency_read_ms, "
            "underperforming, underperforming_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                drive,
                time.time(),
                write_avg_mb_s,
                read_avg_mb_s,
                total_mb,
                int(cache_bypassed),
                iops_write,
                iops_read,
                avg_latency_write_ms,
                avg_latency_read_ms,
                None if underperforming is None else int(underperforming),
                underperforming_reason,
            ),
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
                "iops_write": row["iops_write"],
                "iops_read": row["iops_read"],
                "avg_latency_write_ms": row["avg_latency_write_ms"],
                "avg_latency_read_ms": row["avg_latency_read_ms"],
                "underperforming": None if row["underperforming"] is None else bool(row["underperforming"]),
                "underperforming_reason": row["underperforming_reason"],
            }
            for row in rows
        ]


def record_health_snapshot(
    device_id: str,
    temperature_c: int | None,
    health_percentage: int,
    predicted_failure: bool,
    path: Path = DB_PATH,
) -> None:
    with _connect(path) as conn:
        conn.execute(
            "INSERT INTO health_snapshots (device_id, ts, temperature_c, health_percentage, predicted_failure) "
            "VALUES (?, ?, ?, ?, ?)",
            (device_id, time.time(), temperature_c, health_percentage, int(predicted_failure)),
        )


def get_health_history(device_id: str, limit: int = 200, path: Path = DB_PATH) -> list[dict]:
    with _connect(path) as conn:
        conn.row_factory = sqlite3.Row
        # DESC + LIMIT to cap at the most recent N snapshots, then reversed
        # back to chronological order -- charting wants oldest-to-newest.
        rows = conn.execute(
            "SELECT * FROM health_snapshots WHERE device_id = ? ORDER BY ts DESC LIMIT ?", (device_id, limit)
        ).fetchall()
        return [
            {
                "ts": row["ts"],
                "temperature_c": row["temperature_c"],
                "health_percentage": row["health_percentage"],
                "predicted_failure": bool(row["predicted_failure"]),
            }
            for row in reversed(rows)
        ]
