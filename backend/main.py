import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load OPENROUTER_API_KEY (and any other secrets) from backend/.env before
# the routers below are imported, since advisory.py reads it from the
# process environment.
load_dotenv(Path(__file__).resolve().parent / ".env")

from backend.routers import maps
from backend.routers import forecast
from backend.routers import advisory
from backend.routers import live


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Hourly data refresh + file watcher pushing WebSocket updates
    # (see routers/live.py for both)
    refresher = asyncio.create_task(live.refresh_data_periodically())
    watcher = asyncio.create_task(live.watch_data_files())
    yield
    refresher.cancel()
    watcher.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    """Health check — everything real lives under /maps."""
    return {"status": "ok", "service": "ahmedabad-aqi-backend"}


app.include_router(maps.router, prefix="/maps", tags=["Maps"])
app.include_router(forecast.router, prefix="/maps", tags=["Maps"])
app.include_router(advisory.router, prefix="/maps", tags=["Maps"])
app.include_router(live.router, prefix="/maps", tags=["Maps"])
