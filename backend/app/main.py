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

from . import __version__, autostart, expectations, history
from .benchmark import run_benchmark
from .drives import get_drives
from .health import get_health
from .logging_setup import configure_logging, get_logger
from .notifier import Notifier
from .partitions import get_partitions
from .paths import ASSETS_DIR, FRONTEND_DIR
from .settings import load_settings, save_settings

configure_logging()
logger = get_logger("main")


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
# device_id -> was it over temperature_alert_c last check -- kept separate
# from _last_notified since that threshold is user-configurable and only
# applies when a value is set (unlike the other two, always-on checks).
_last_temp_alert: dict[str, bool] = {}

_PHYSICAL_DRIVE_KEY_RE = re.compile(r"PhysicalDrive(\d+)", re.IGNORECASE)
# device_id -> (read_bytes, write_bytes, monotonic timestamp) from the
# previous tick, so throughput can be derived from psutil's cumulative
# counters by diffing against last time rather than needing a second,
# blocking sleep-and-measure step of its own.
_last_io_counters: dict[str, tuple[int, int, float]] = {}

_HEALTH_SNAPSHOT_INTERVAL_S = 60.0
# device_id -> monotonic timestamp of its last recorded health_snapshots
# row -- snapshots are throttled well below poll_interval_s so history.db
# doesn't grow by a row per drive every few seconds.
_last_health_snapshot: dict[str, float] = {}


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
            await asyncio.to_thread(_record_health_snapshots, health)
        except Exception:
            logger.exception("poll loop error")
        await asyncio.sleep(settings.poll_interval_s)


def _record_health_snapshots(health: list[dict]) -> None:
    now = time.monotonic()
    for entry in health:
        device_id = entry["device_id"]
        if now - _last_health_snapshot.get(device_id, 0.0) < _HEALTH_SNAPSHOT_INTERVAL_S:
            continue
        history.record_health_snapshot(
            device_id, entry["temperature_c"], entry["health_percentage"], entry["predicted_failure"]
        )
        _last_health_snapshot[device_id] = now


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

        if settings.temperature_alert_c is not None and entry["temperature_c"] is not None:
            key = f"temp:{entry['device_id']}"
            is_hot = entry["temperature_c"] >= settings.temperature_alert_c
            was_hot = _last_temp_alert.get(key, False)
            if is_hot and not was_hot:
                notifier.notify_high_temperature(entry["model"], entry["temperature_c"], settings.temperature_alert_c)
            _last_temp_alert[key] = is_hot


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
    temperature_alert_c: Optional[int] = None


@app.get("/api/app-info")
async def app_info():
    return {"name": "DiskInfo", "version": __version__}


@app.get("/api/settings")
async def api_get_settings():
    # The scheduled task (see autostart.py) is ground truth -- Task
    # Scheduler's UI (or a future reinstall) can toggle it outside the
    # app, so don't trust a possibly-stale value sitting in settings.json.
    settings.autostart = await asyncio.to_thread(autostart.is_enabled)
    return asdict(settings)


@app.put("/api/settings")
async def api_update_settings(update: SettingsUpdate):
    # include=model_fields_set (not exclude_none=True) so a client can
    # explicitly clear a nullable field like temperature_alert_c back to
    # null -- exclude_none would make "not sent" and "sent as null"
    # indistinguishable, silently dropping the clear.
    patch = update.model_dump(include=update.model_fields_set)
    if "autostart" in patch:
        try:
            await asyncio.to_thread(autostart.enable if patch["autostart"] else autostart.disable)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
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


@app.get("/api/health/history")
async def api_health_history(device_id: str, limit: int = 200):
    return await asyncio.to_thread(history.get_health_history, device_id, limit)


@app.get("/api/partitions")
async def api_partitions():
    return await asyncio.to_thread(get_partitions)


def _find_drive_category(drives: list[dict], letter: str) -> tuple[str, str]:
    mountpoint = f"{letter}:\\"
    for drive in drives:
        if any(p["mountpoint"].upper() == mountpoint.upper() for p in drive["partitions"]):
            return drive["media_type"], drive["bus_type"]
    return "Unknown", "Unknown"


async def _run_benchmark_task(letter: str, total_mb: int) -> None:
    mountpoint = f"{letter}:\\"
    media_type, bus_type = _find_drive_category(await asyncio.to_thread(get_drives), letter)
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
            underperforming, reason = expectations.evaluate(media_type, bus_type, event["write_avg_mb_s"])
            event["underperforming"] = underperforming
            event["underperforming_reason"] = reason
            await asyncio.to_thread(
                history.record_run,
                letter,
                event["write_avg_mb_s"],
                event["read_avg_mb_s"],
                total_mb,
                event["cache_bypassed"],
                event.get("iops_write"),
                event.get("iops_read"),
                event.get("avg_latency_write_ms"),
                event.get("avg_latency_read_ms"),
                underperforming,
                reason,
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
        # smart_attributes is a nested list -- fine in the drives/health
        # views on screen, but not tabular, so it's left out of this flat
        # export rather than dumping a Python repr into a CSV cell.
        return [{k: v for k, v in entry.items() if k != "smart_attributes"} for entry in get_health()]
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
