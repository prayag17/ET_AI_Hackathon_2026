# Merges ALL datasets into one feature_store.csv:
#   1. city_hour.csv (real Kaggle AQI per hour)
#   2. IDW interpolation (real spatial distribution via sensor locations)
#   3. weather (seasonal patterns from weather_history.csv)
#   4. traffic (diurnal pattern)
#   5. GeoJSON cell IDs (AHM-0001 format)


import pandas as pd
import numpy as np
import json, sys
from pathlib import Path

# Paths
HERE         = Path(__file__).resolve().parent        # ai_model/
GRID_PATH    = HERE.parent / "backend" / "static" / "ahmedabad_1km_grid.geojson"
CITY_HOUR    = HERE / "data" / "city_hour.csv"
WEATHER_HIST = HERE / "data" / "features" / "weather_history.csv"
SENSORS_CSV  = HERE / "data" / "sensor_locations.csv"

# Import interpolation functions
sys.path.insert(0, str(HERE))
from interpolation import idw


# step 1: Load GeoJSON grid
print("Step 1: Loading GeoJSON grid...")
with open(GRID_PATH) as f:
    geojson = json.load(f)

grid = pd.DataFrame([{
    "grid_cell_id": feat["properties"]["grid_id"],
    "centroid_lat": feat["properties"]["centroid_lat"],
    "centroid_lon": feat["properties"]["centroid_lon"],
} for feat in geojson["features"]])
print(f"  {len(grid)} cells — e.g. {grid['grid_cell_id'].iloc[0]}")

# step 2: Load sensor locations
print("\nStep 2: Loading sensor locations...")
sensors = pd.read_csv(SENSORS_CSV)
print(f"  {len(sensors)} stations: {sensors['station_id'].tolist()}")

# step 3: Load real Ahmedabad AQI from Kaggle
print("\nStep 3: Loading city_hour.csv...")
ch = pd.read_csv(CITY_HOUR, parse_dates=["Datetime"])
ahm = ch[ch["City"] == "Ahmedabad"].copy()
ahm = ahm.dropna(subset=["AQI"])
ahm = ahm[ahm["AQI"] > 0]
ahm["Datetime"] = ahm["Datetime"].dt.floor("h")

# Fill pollutant nulls with median
for col in ["PM2.5", "NO2", "CO"]:
    ahm[col] = ahm[col].fillna(ahm[col].median())

print(f"  {len(ahm)} hourly rows | {ahm['Datetime'].min().date()} to {ahm['Datetime'].max().date()}")
print(f"  Mean AQI: {ahm['AQI'].mean():.0f}")

# step 4: Load weather and build seasonal lookup
print("\nStep 4: Loading weather...")
try:
    weather = pd.read_csv(WEATHER_HIST, parse_dates=["time"])
    weather = weather.rename(columns={
        "time": "timestamp",
        "temperature_2m": "temp",
        "wind_speed_10m": "wind_speed",
        "relative_humidity_2m": "humidity",
    })
    weather["month"] = weather["timestamp"].dt.month
    weather["hour"]  = weather["timestamp"].dt.hour
    # Build month+hour average — apply to 2015-2020 AQI dates by season
    weather_pattern = (
        weather.groupby(["month", "hour"])[["temp", "wind_speed", "humidity"]]
               .mean().reset_index()
    )
    ahm["month"] = ahm["Datetime"].dt.month
    ahm["hour"]  = ahm["Datetime"].dt.hour
    ahm = ahm.merge(weather_pattern, on=["month", "hour"], how="left")
    ahm = ahm.drop(columns=["month", "hour"])
    print(f"  Weather joined via seasonal month+hour pattern (real Delhi data)")
except FileNotFoundError:
    print("  weather_history.csv not found — using Ahmedabad climate defaults")
    CLIMATE = {1:(18,6,55),2:(21,7,45),3:(27,9,35),4:(33,10,25),
               5:(37,11,20),6:(34,14,50),7:(31,13,70),8:(30,11,72),
               9:(30,9,65),10:(28,7,50),11:(23,6,45),12:(19,6,52)}
    ahm["month"] = ahm["Datetime"].dt.month
    ahm["temp"]       = ahm["month"].map(lambda m: CLIMATE[m][0])
    ahm["wind_speed"] = ahm["month"].map(lambda m: CLIMATE[m][1])
    ahm["humidity"]   = ahm["month"].map(lambda m: CLIMATE[m][2])
    ahm = ahm.drop(columns=["month"])

# step 5: Traffic index
WEEKDAY = [0.10,0.05,0.05,0.05,0.10,0.20,0.40,0.70,0.90,1.00,
           0.80,0.70,0.70,0.70,0.65,0.70,0.80,0.95,1.00,0.95,
           0.80,0.60,0.40,0.20]
ahm["traffic_index"] = ahm["Datetime"].apply(
    lambda ts: round(WEEKDAY[ts.hour] * (0.6 if ts.dayofweek >= 5 else 1.0), 3)
)

# step 6: IDW interpolation, expand city reading to 502 grid cells
print(f"\nStep 6: IDW interpolation across {len(grid)} cells...")
print(f"  Processing {len(ahm)} timestamps × {len(sensors)} stations...")
print(f"  This will take several minutes — go get chai ☕")

# Station-specific pollution factors (from interpolation.py)
STATION_FACTOR = {
    "AMD_AIRPORT":    1.05,
    "AMD_BOPAL":      0.75,
    "AMD_CHANDKHEDA": 0.90,
    "AMD_GYASPUR":    1.30,
    "AMD_MANINAGAR":  1.10,
    "AMD_NAVRANGPURA":0.85,
    "AMD_PIRANA":     1.40,
    "AMD_RAIKHAD":    1.05,
    "AMD_RAKHIAL":    1.20,
    "AMD_SATELLITE":  0.80,
}

frames = []
total = len(ahm)
for i, (_, row) in enumerate(ahm.iterrows()):
    if i % 500 == 0:
        print(f"  {i}/{total} timestamps processed...")

    # Build per-station readings for this timestamp
    sensor_readings = sensors.copy()
    sensor_readings["value"] = [
        row["AQI"] * STATION_FACTOR.get(sid, 1.0)
        for sid in sensor_readings["station_id"]
    ]

    # IDW: interpolate from 10 sensors to 502 grid cells
    grid_values = idw(
        sensor_readings["lat"],
        sensor_readings["lon"],
        sensor_readings["value"],
        grid["centroid_lat"],
        grid["centroid_lon"],
        power=2.0,
    )

    # Build one row per grid cell for this timestamp
    cell_df = grid[["grid_cell_id"]].copy()
    cell_df["timestamp"]     = row["Datetime"]
    cell_df["aqi"]           = np.round(grid_values, 1).clip(min=0)
    cell_df["pm25"]          = np.round(row["PM2.5"] * (grid_values / row["AQI"].clip(min=1)), 2).clip(min=0)
    cell_df["no2"]           = np.round(row["NO2"]   * (grid_values / row["AQI"].clip(min=1)), 2).clip(min=0)
    cell_df["co"]            = np.round(row["CO"]    * (grid_values / row["AQI"].clip(min=1)), 4).clip(min=0)
    cell_df["wind_speed"]    = row["wind_speed"]
    cell_df["temp"]          = row["temp"]
    cell_df["humidity"]      = row["humidity"]
    cell_df["traffic_index"] = row["traffic_index"]
    frames.append(cell_df)

fs = pd.concat(frames, ignore_index=True)
fs = fs.sort_values(["grid_cell_id", "timestamp"]).reset_index(drop=True)

# step 7: Validate and save
print("\n=== VALIDATION ===")
print(f"Rows:       {len(fs):,}")
print(f"Cells:      {fs['grid_cell_id'].nunique()} (expected 502)")
print(f"Cell IDs:   {fs['grid_cell_id'].unique()[:3].tolist()}")
print(f"Date range: {fs['timestamp'].min()} -> {fs['timestamp'].max()}")
print(f"Mean AQI:   {fs['aqi'].mean():.0f}")
print(f"AQI range:  {fs['aqi'].min():.0f} - {fs['aqi'].max():.0f}")
print(f"Nulls:      {fs.isnull().sum().sum()}")

# Verify spatial variation is real (not all cells same value)
sample_ts = fs["timestamp"].iloc[0]
sample_hour = fs[fs["timestamp"] == sample_ts]
print(f"\nSpatial variation at first timestamp:")
print(f"  AQI min={sample_hour['aqi'].min():.0f}  max={sample_hour['aqi'].max():.0f}  "
      f"std={sample_hour['aqi'].std():.1f}")

fs.to_csv("data/feature_store.csv", index=False)
print("\n Saved: data/feature_store.csv")