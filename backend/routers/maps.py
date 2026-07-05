import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

# I hate python paths
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
GRID_PATH = STATIC_DIR / "ahmedabad_1km_grid.geojson"
BOUNDARY_PATH = STATIC_DIR / "ahmedabad_boundary.geojson"


@router.get("/getMap", tags=["Maps"])
async def get_map():
    return json.loads(GRID_PATH.read_text(encoding="utf-8"))


@router.get("/getBoundary", tags=["Maps"])
async def get_boundary():
    return json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
