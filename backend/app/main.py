"""FastAPI app: REST endpoints serve drive/health/partition snapshots and
kick off benchmarks; a WebSocket streams live usage ticks and benchmark
progress. Also serves frontend/ as static files so the whole app is
reachable at http://127.0.0.1:<port>/ during development, without pywebview."""

from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import __version__
from .benchmark import run_benchmark
from .drives import get_drives
from .health import get_health
from .notifier import Notifier
from .partitions import get_partitions
from .paths import ASSETS_DIR, FRONTEND_DIR
from .settings import load_settings


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


async def _poll_loop() -> None:
    while True:
        try:
            drives = await asyncio.to_thread(get_drives)
            health = await asyncio.to_thread(get_health)
            await manager.broadcast({"type": "tick", "data": {"drives": drives, "health": health}})

            if settings.notifications_enabled:
                _check_thresholds(drives, health)
        except Exception as exc:
            print(f"[poll] error: {exc}")
        await asyncio.sleep(settings.poll_interval_s)


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


@app.get("/api/app-info")
async def app_info():
    return {"name": "DiskInfo", "version": __version__}


@app.get("/api/drives")
async def api_drives():
    return await asyncio.to_thread(get_drives)


@app.get("/api/health")
async def api_health():
    return await asyncio.to_thread(get_health)


@app.get("/api/partitions")
async def api_partitions():
    return await asyncio.to_thread(get_partitions)


async def _run_benchmark_task(letter: str) -> None:
    mountpoint = f"{letter}:\\"
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _worker() -> None:
        for event in run_benchmark(mountpoint):
            loop.call_soon_threadsafe(queue.put_nowait, event)
        loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_worker, daemon=True).start()

    while True:
        event = await queue.get()
        if event is None:
            break
        await manager.broadcast({"type": "benchmark_progress", "data": {**event, "drive": letter}})


@app.post("/api/benchmark/{letter}")
async def api_benchmark(letter: str):
    asyncio.create_task(_run_benchmark_task(letter.rstrip(":").upper()))
    return {"status": "started", "drive": letter}


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
