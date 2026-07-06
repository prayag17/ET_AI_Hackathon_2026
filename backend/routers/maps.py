import json
from pathlib import Path
import csv
from fastapi import APIRouter

router = APIRouter()

# I hate python paths
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
GRID_PATH = STATIC_DIR / "ahmedabad_1km_grid.geojson"
BOUNDARY_PATH = STATIC_DIR / "ahmedabad_boundary.geojson"
POLLUTION_CSV = Path(__file__).resolve(
).parents[2] / "ai_model" / "data" / "grid_pollution_demo.csv"

@router.get("/getMap", tags=["Maps"])
async def get_map():
    return json.loads(GRID_PATH.read_text(encoding="utf-8"))


@router.get("/getBoundary", tags=["Maps"])
async def get_boundary():
    return json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))


@router.get("/getPollution", tags=["Maps"])
async def get_pollution():
    with POLLUTION_CSV.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        "datetime": rows[0]["datetime"],
        "values": {r["grid_id"]: float(r["value"]) for r in rows},
    }
