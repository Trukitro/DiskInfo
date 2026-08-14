"""FastAPI app: REST endpoints serve drive/health/partition snapshots and
kick off benchmarks; a WebSocket streams live usage ticks and benchmark
progress. Also serves frontend/ as static files so the whole app is
reachable at http://127.0.0.1:<port>/ during development, without pywebview."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import re
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import psutil
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__, autostart, history
from .benchmark import run_benchmark
from .drives import get_drives
from .health import get_health
from .notifier import Notifier
from .partitions import get_partitions
from .paths import ASSETS_DIR, FRONTEND_DIR
from .settings import load_settings, save_settings


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
notifier = Notifier()
settings = load_settings()
# device_id -> last state we already notified about, so a drive sitting at
# 95% full or with a standing predicted-failure flag doesn't re-toast every
# poll interval -- only on the state actually changing.
_last_notified: dict[str, tuple[bool, bool]] = {}

_PHYSICAL_DRIVE_KEY_RE = re.compile(r"PhysicalDrive(\d+)", re.IGNORECASE)
# device_id -> (read_bytes, write_bytes, monotonic timestamp) from the
# previous tick, so throughput can be derived from psutil's cumulative
# counters by diffing against last time rather than needing a second,
# blocking sleep-and-measure step of its own.
_last_io_counters: dict[str, tuple[int, int, float]] = {}


async def _poll_loop() -> None:
    while True:
        try:
            drives = await asyncio.to_thread(get_drives)
            health = await asyncio.to_thread(get_health)
            io_activity = await asyncio.to_thread(_compute_io_activity)
            await manager.broadcast(
                {"type": "tick", "data": {"drives": drives, "health": health, "io_activity": io_activity}}
            )

            if settings.notifications_enabled:
                _check_thresholds(drives, health)
        except Exception as exc:
            print(f"[poll] error: {exc}")
        await asyncio.sleep(settings.poll_interval_s)


def _compute_io_activity() -> dict[str, dict]:
    """Per-physical-disk read/write throughput, derived by diffing
    psutil's cumulative disk_io_counters against the previous tick. Keyed
    by the same device_id format (\\\\.\\PHYSICALDRIVEn) drives.py/health.py
    use, so the frontend can correlate activity with a specific drive card
    without a second lookup."""
    now = time.monotonic()
    activity: dict[str, dict] = {}
    try:
        counters = psutil.disk_io_counters(perdisk=True)
    except Exception:
        return activity

    for psutil_key, counter in counters.items():
        match = _PHYSICAL_DRIVE_KEY_RE.search(psutil_key)
        if not match:
            continue
        device_id = f"\\\\.\\PHYSICALDRIVE{match.group(1)}"

        prev = _last_io_counters.get(device_id)
        if prev is not None:
            prev_read, prev_write, prev_time = prev
            elapsed = now - prev_time
            if elapsed > 0:
                activity[device_id] = {
                    "read_bps": max(0.0, (counter.read_bytes - prev_read) / elapsed),
                    "write_bps": max(0.0, (counter.write_bytes - prev_write) / elapsed),
                }
        _last_io_counters[device_id] = (counter.read_bytes, counter.write_bytes, now)

    return activity


def _check_thresholds(drives: list[dict], health: list[dict]) -> None:
    for drive in drives:
        for partition in drive["partitions"]:
            key = f"space:{partition['mountpoint']}"
            is_low = partition["percent"] >= settings.low_space_pct
            was_low = _last_notified.get(key, (False, False))[0]
            if is_low and not was_low:
                notifier.notify_low_space(partition["mountpoint"], partition["percent"])
            _last_notified[key] = (is_low, False)

    for entry in health:
        key = f"health:{entry['device_id']}"
        failing = entry["predicted_failure"]
        was_failing = _last_notified.get(key, (False, False))[1]
        if failing and not was_failing:
            notifier.notify_predicted_failure(entry["model"], entry["reason"])
        _last_notified[key] = (False, failing)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_poll_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


class SettingsUpdate(BaseModel):
    poll_interval_s: Optional[float] = None
    low_space_pct: Optional[float] = None
    notifications_enabled: Optional[bool] = None
    port: Optional[int] = None
    autostart: Optional[bool] = None
    last_selected_drive: Optional[str] = None


@app.get("/api/app-info")
async def app_info():
    return {"name": "DiskInfo", "version": __version__}


@app.get("/api/settings")
async def api_get_settings():
    # Registry is ground truth for autostart -- Task Manager's Startup tab
    # (or the installer) can toggle it outside the app, so don't trust a
    # possibly-stale value sitting in settings.json.
    settings.autostart = await asyncio.to_thread(autostart.is_enabled)
    return asdict(settings)


@app.put("/api/settings")
async def api_update_settings(update: SettingsUpdate):
    patch = update.model_dump(exclude_none=True)
    if "autostart" in patch:
        await asyncio.to_thread(autostart.enable if patch["autostart"] else autostart.disable)
    for key, value in patch.items():
        setattr(settings, key, value)
    await asyncio.to_thread(save_settings, settings)
    return asdict(settings)


@app.get("/api/drives")
async def api_drives():
    return await asyncio.to_thread(get_drives)


@app.get("/api/health")
async def api_health():
    return await asyncio.to_thread(get_health)


@app.get("/api/partitions")
async def api_partitions():
    return await asyncio.to_thread(get_partitions)


async def _run_benchmark_task(letter: str, total_mb: int) -> None:
    mountpoint = f"{letter}:\\"
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _worker() -> None:
        for event in run_benchmark(mountpoint, total_mb=total_mb):
            loop.call_soon_threadsafe(queue.put_nowait, event)
        loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_worker, daemon=True).start()

    while True:
        event = await queue.get()
        if event is None:
            break
        if event.get("phase") == "done":
            await asyncio.to_thread(
                history.record_run,
                letter,
                event["write_avg_mb_s"],
                event["read_avg_mb_s"],
                total_mb,
                event["cache_bypassed"],
            )
        await manager.broadcast({"type": "benchmark_progress", "data": {**event, "drive": letter}})


@app.post("/api/benchmark/{letter}")
async def api_benchmark(letter: str, total_mb: int = 200):
    total_mb = max(10, min(total_mb, 5000))  # sane bounds regardless of what the client sends
    asyncio.create_task(_run_benchmark_task(letter.rstrip(":").upper(), total_mb))
    return {"status": "started", "drive": letter, "total_mb": total_mb}


@app.get("/api/benchmark/history")
async def api_benchmark_history(drive: Optional[str] = None, limit: int = 20):
    return await asyncio.to_thread(history.get_history, drive, limit)


_EXPORT_VIEWS = {"drives", "health", "partitions", "benchmark_history"}


def _export_rows(view: str, drive: Optional[str]) -> list[dict]:
    """Flattens each view's nested JSON shape into one row per record --
    a plain CSV/JSON dump of data already shown on screen, not a reporting
    engine (see the "export vs. reporting" scope note in
    DiskInfo-project-plan.md)."""
    if view == "drives":
        return [
            {
                "device_id": d["device_id"],
                "model": d["model"],
                "bus_type": d["bus_type"],
                "media_type": d["media_type"],
                "size_bytes": d["size"],
                "mountpoint": p["mountpoint"],
                "used_bytes": p["used"],
                "total_bytes": p["total"],
                "percent": p["percent"],
            }
            for d in get_drives()
            for p in d["partitions"]
        ]
    if view == "health":
        return get_health()
    if view == "partitions":
        return [
            {
                "disk_number": d["disk_number"],
                "model": d["model"],
                "letter": s["letter"],
                "type": "Primary" if s["primary"] else "Logical",
                "filesystem": s["filesystem"],
                "size_bytes": s["size"],
                "percent_used": s["percent_used"],
            }
            for d in get_partitions()
            for s in d["segments"]
            if not s["unallocated"]
        ]
    if view == "benchmark_history":
        return history.get_history(drive, limit=1000)
    raise ValueError(f"unknown export view: {view}")


@app.get("/api/export")
async def api_export(view: str, format: str = "csv", drive: Optional[str] = None):
    if view not in _EXPORT_VIEWS:
        raise HTTPException(status_code=400, detail=f"unknown view '{view}', expected one of {sorted(_EXPORT_VIEWS)}")
    if format not in ("csv", "json"):
        raise HTTPException(status_code=400, detail=f"unknown format '{format}', expected 'csv' or 'json'")

    rows = await asyncio.to_thread(_export_rows, view, drive)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"diskinfo-{view}-{timestamp}.{format}"

    if format == "json":
        body = json.dumps(rows, indent=2)
        media_type = "application/json"
    else:
        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        body = buf.getvalue()
        media_type = "text/csv"

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
