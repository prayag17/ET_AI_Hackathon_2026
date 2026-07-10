from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
import json
from pathlib import Path

# Fix the import path so FastAPI can find ai_model
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from ai_model.data import advisor

router = APIRouter()

FORECAST_JSON = Path(__file__).resolve().parents[1] / "forecast_demo.json"

@router.get("/getAdvisory", tags=["Maps"])
async def get_advisory():
    """
    Returns GRAP advisory recommendations based on the 72-hour forecast.
    """
    # 1. Load the forecast
    with open(FORECAST_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    snapshots = data["snapshots"]
    
    # 2. Convert to DataFrame format expected by advisor.py
    # Expected format for detect_events: DataFrame with [datetime, grid_cell_id, aqi]
    rows = []
    base_dt = pd.to_datetime(data["base_datetime"])
    for snap in snapshots:
        offset = snap["offset_hours"]
        dt = base_dt + pd.Timedelta(hours=offset)
        for gid, aqi in snap["values"].items():
            rows.append({
                "datetime": dt,
                "grid_cell_id": gid,
                "aqi": aqi
            })
            
    df = pd.DataFrame(rows)
    
    # 3. Detect severe pollution events (Very Poor or Severe)
    events = advisor.detect_events(df, base_dt, min_cat="Very Poor")
    
    # 4. Generate recommendations
    recs = advisor.recommend(events)
    
    return {"advisories": recs}
