# convert_kaggle.py
# FINAL VERSION — builds feature_store.csv from real Kaggle data
#
# INPUT:  data/city_hour.csv
#         ../backend/static/ahmedabad_1km_grid.geojson
#
# OUTPUT: data/feature_store.csv
#
# Run from ai_model/ folder:  python convert_kaggle.py

import pandas as pd
import numpy as np
import json, os

# ── 1. Load GeoJSON cell IDs ─────────────────────────────────────────────────
print("Loading GeoJSON...")
with open("../backend/static/ahmedabad_1km_grid.geojson") as f:
    grid = json.load(f)

cells = pd.DataFrame([{
    "grid_cell_id": feat["properties"]["grid_id"],
    "centroid_lat": feat["properties"]["centroid_lat"],
    "centroid_lon": feat["properties"]["centroid_lon"],
} for feat in grid["features"]])
print(f"  {len(cells)} cells — e.g. {cells['grid_cell_id'].iloc[0]}")

# ── 2. Load real Ahmedabad data ───────────────────────────────────────────────
print("\nLoading city_hour.csv...")
df = pd.read_csv("data/city_hour.csv", parse_dates=["Datetime"])
ahm = df[df["City"] == "Ahmedabad"].copy()
ahm = ahm.dropna(subset=["AQI"])
ahm = ahm[ahm["AQI"] > 0]
ahm["Datetime"] = ahm["Datetime"].dt.floor("h")
print(f"  {len(ahm)} rows | {ahm['Datetime'].min().date()} to {ahm['Datetime'].max().date()} | mean AQI {ahm['AQI'].mean():.0f}")

# Fill missing pollutant columns
for col in ["PM2.5", "NO2", "CO"]:
    ahm[col] = ahm[col].fillna(ahm[col].median())

# Traffic index from diurnal pattern
WEEKDAY = [0.10,0.05,0.05,0.05,0.10,0.20,0.40,0.70,0.90,1.00,
           0.80,0.70,0.70,0.70,0.65,0.70,0.80,0.95,1.00,0.95,
           0.80,0.60,0.40,0.20]
def traffic_index(ts):
    return round(WEEKDAY[ts.hour] * (0.6 if ts.dayofweek >= 5 else 1.0), 3)
ahm["traffic_index"] = ahm["Datetime"].apply(traffic_index)

# ── 3. Expand to 502 grid cells ───────────────────────────────────────────────
print(f"\nExpanding to {len(cells)} cells (this takes ~2 minutes)...")
frames = []
for i, cell in cells.iterrows():
    cell_df = ahm[["Datetime","AQI","PM2.5","NO2","CO","traffic_index"]].copy()
    cell_df["grid_cell_id"] = cell["grid_cell_id"]
    np.random.seed(i)
    factor = np.clip(1.0 + (cell["centroid_lat"] - 23.03) * 0.5, 0.85, 1.20) * np.random.uniform(0.92, 1.08)
    cell_df["aqi"]  = (cell_df["AQI"]   * factor).round(1).clip(lower=0)
    cell_df["pm25"] = (cell_df["PM2.5"] * factor).round(2).clip(lower=0)
    cell_df["no2"]  = (cell_df["NO2"]   * factor).round(2).clip(lower=0)
    cell_df["co"]   = (cell_df["CO"]    * factor).round(4).clip(lower=0)
    frames.append(cell_df[["Datetime","grid_cell_id","aqi","pm25","no2","co","traffic_index"]])

fs = pd.concat(frames, ignore_index=True)
fs = fs.rename(columns={"Datetime": "timestamp"})
fs = fs.sort_values(["grid_cell_id","timestamp"]).reset_index(drop=True)

print(f"\n=== RESULT ===")
print(f"Rows: {len(fs):,} | Cells: {fs['grid_cell_id'].nunique()} | Mean AQI: {fs['aqi'].mean():.0f}")
print(f"Cell IDs: {fs['grid_cell_id'].unique()[:3].tolist()}")
print(f"Nulls: {fs.isnull().sum().sum()}")

os.makedirs("data", exist_ok=True)
fs.to_csv("data/feature_store.csv", index=False)
print("\n✅ Saved: data/feature_store.csv")
print("\nNow run in order:")
print("  1. python data/pollution_event_calender.py")
print("  2. python features.py")
print("  3. python baseline.py")
print("  4. python train.py")
print("  5. python scorecard.py")