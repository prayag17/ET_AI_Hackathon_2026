import pandas as pd
import json
import numpy as np

# Load the large prediction file
print("Loading model_predictions.csv...")
df = pd.read_csv("ai_model/data/model_predictions.csv", parse_dates=["timestamp"])

# We must match the exact date that interpolation.py used for the T=0 snapshot
grid_df = pd.read_csv("ai_model/data/grid_pollution_demo.csv")
target_dt_str = grid_df["datetime"].iloc[0]
target_dt = pd.to_datetime(target_dt_str)

slice_df = df[df["timestamp"] == target_dt].copy()

if slice_df.empty:
    print(f"Warning: No LightGBM forecast data for {target_dt}. Using synthetic baseline for the timeline.")
    # Create empty dataframe so it gracefully falls back to base_aqi
    slice_df = pd.DataFrame([{"grid_cell_id": gid, "aqi": val, "model_pred_24h": val, "model_pred_48h": val, "model_pred_72h": val} for gid, val in zip(grid_df["grid_id"], grid_df["value"])])


# The predictions are for 24h, 48h, 72h. We also need T=0 from the actual AQI
# We will interpolate linearly for hourly data between T=0, 24, 48, 72
snapshots = []

# Map grid to T=0, T=24, T=48, T=72
cells = slice_df["grid_cell_id"].unique()
base_aqi = {row["grid_cell_id"]: row["aqi"] for _, row in slice_df.iterrows()}
pred_24 = {row["grid_cell_id"]: row["model_pred_24h"] for _, row in slice_df.iterrows()}
pred_48 = {row["grid_cell_id"]: row["model_pred_48h"] for _, row in slice_df.iterrows()}
pred_72 = {row["grid_cell_id"]: row["model_pred_72h"] for _, row in slice_df.iterrows()}

for h in range(73):
    values = {}
    for gid in cells:
        v0 = base_aqi.get(gid, 50)
        v24 = pred_24.get(gid, v0)
        v48 = pred_48.get(gid, v24)
        v72 = pred_72.get(gid, v48)
        
        # simple linear interpolation between the keyframes
        if h <= 24:
            ratio = h / 24.0
            val = v0 + (v24 - v0) * ratio
        elif h <= 48:
            ratio = (h - 24) / 24.0
            val = v24 + (v48 - v24) * ratio
        else:
            ratio = (h - 48) / 24.0
            val = v48 + (v72 - v48) * ratio
            
        # Add some slight noise so the curve isn't perfectly straight lines
        noise = np.sin(h * np.pi / 6) * 2.0  # diurnal wiggle
        values[gid] = round(max(0, val + noise), 1)
        
    snapshots.append({
        "offset_hours": h,
        "base_datetime": target_dt.isoformat(),
        "values": values
    })

out_data = {
    "base_datetime": target_dt.isoformat(),
    "snapshots": snapshots
}

out_path = "backend/forecast_demo.json"
with open(out_path, "w") as f:
    json.dump(out_data, f)
print(f"Exported {len(snapshots)} hourly snapshots to {out_path}")
