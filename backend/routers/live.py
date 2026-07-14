"""
Live-update channel (issue #45) — keeps dashboards current end to end:

1. refresh_data_periodically() re-runs live_inference.py every hour, which
   pulls the latest Open-Meteo readings and rewrites grid_pollution_demo.csv
   plus forecast_demo.json — so the data keeps itself up to date, no manual
   pipeline runs needed.
2. watch_data_files() polls the pollution CSV's mtime and broadcasts
   {"type": "data_updated", "source": "pollution"} to every client connected
   to ws://…/maps/ws when it changes (whether the refresher rewrote it or a
   teammate ran the pipeline by hand).

Both tasks are started from the app's lifespan in main.py. The CSV is the
file /getPollution and /getForecast derive from, so one signal covers the
live snapshot, the forecasts, and the advisories computed from them.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]
POLLUTION_CSV = REPO_ROOT / "ai_model" / "data" / "grid_pollution_demo.csv"
LIVE_INFERENCE_SCRIPT = REPO_ROOT / "live_inference.py"
POLL_SECONDS = 5.0

# Open-Meteo publishes hourly readings, so refreshing more often buys
# nothing. Override with the LIVE_REFRESH_SECONDS env var; 0 disables the
# auto-refresh loop entirely (the WebSocket watcher still runs).
REFRESH_SECONDS = float(os.environ.get("LIVE_REFRESH_SECONDS", 3600))
RETRY_SECONDS = 600.0
PIPELINE_TIMEOUT_SECONDS = 300.0


class ConnectionManager:
    """Tracks open sockets and fans a message out to all of them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)


manager = ConnectionManager()


@router.websocket("/ws")
async def live_updates(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # Clients never need to send anything — this loop just keeps the
            # socket open and surfaces disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def _run_pipeline_blocking() -> subprocess.CompletedProcess:
    """Plain synchronous subprocess — asyncio's subprocess API isn't
    available on every Windows event loop (uvicorn's reload worker can run
    a Selector loop, where create_subprocess_exec raises), so this runs in
    a thread via asyncio.to_thread instead."""
    return subprocess.run(
        [sys.executable, str(LIVE_INFERENCE_SCRIPT)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=PIPELINE_TIMEOUT_SECONDS,
        # The script prints emoji; without UTF-8 forced, a piped stdout on
        # Windows falls back to cp1252 and the child dies mid-run.
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )


async def _run_live_inference() -> bool:
    """Run live_inference.py once in this venv; True on success."""
    try:
        proc = await asyncio.to_thread(_run_pipeline_blocking)
    except subprocess.TimeoutExpired:
        print(
            "[live-refresh] live_inference.py timed out — keeping previous data",
            flush=True,
        )
        return False
    if proc.returncode != 0:
        tail = proc.stdout.decode("utf-8", errors="replace")[-600:]
        print(
            f"[live-refresh] live_inference.py failed (exit {proc.returncode}) "
            f"— keeping previous data\n{tail}",
            flush=True,
        )
        return False
    print("[live-refresh] data refreshed from Open-Meteo", flush=True)
    return True


async def refresh_data_periodically() -> None:
    """Keep the pollution CSV up to date by re-running the live pipeline.

    Only produces the data — the mtime watcher below notices the rewritten
    CSV and pushes the update to connected dashboards. A failed run keeps
    the previous snapshot and retries sooner.
    """
    if REFRESH_SECONDS <= 0 or not LIVE_INFERENCE_SCRIPT.exists():
        return
    while True:
        # If the snapshot is still fresh (say, a dev-server reload a minute
        # after the last run), wait out the remainder of the hour instead of
        # hitting the API on every restart.
        try:
            age = time.time() - POLLUTION_CSV.stat().st_mtime
        except OSError:
            age = REFRESH_SECONDS
        if age < REFRESH_SECONDS:
            await asyncio.sleep(REFRESH_SECONDS - age)
        ok = False
        try:
            ok = await _run_live_inference()
        except Exception as exc:  # never let the refresh loop die silently
            print(f"[live-refresh] unexpected error: {exc!r}", flush=True)
        if not ok:
            await asyncio.sleep(RETRY_SECONDS)


async def watch_data_files() -> None:
    """Poll the pollution CSV's mtime; notify clients when it changes.

    Any writer counts — the hourly refresher above or a teammate running
    live_inference.py / interpolation.py by hand."""
    last_mtime: float | None = None
    while True:
        try:
            mtime = POLLUTION_CSV.stat().st_mtime
        except OSError:
            mtime = None
        if last_mtime is not None and mtime is not None and mtime != last_mtime:
            await manager.broadcast({"type": "data_updated", "source": "pollution"})
        if mtime is not None:
            last_mtime = mtime
        await asyncio.sleep(POLL_SECONDS)
