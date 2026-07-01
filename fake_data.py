import pandas as pd
import numpy as np

np.random.seed(42)

# Assuming the city has 50 grid cells and we have 60 days of hourly data
N_CELLS = 50
N_DAYS = 60

cell_ids = [f"cell_{i:03d}" for i in range(N_CELLS)]
timestamps = pd.date_range("2025-09-01", periods=N_DAYS * 24, freq="h")

rows = []
for cell in cell_ids:
    base_aqi = np.random.uniform(80, 200)
    for ts in timestamps:
        hour_effect = 30 * np.sin((ts.hour - 6) / 24 * 2 * np.pi)
        day_trend = (ts - timestamps[0]).days * 0.5  # slowly rising
        noise = np.random.normal(0, 15)
        aqi = max(20, base_aqi + hour_effect + day_trend + noise)

        rows.append({
            "timestamp": ts,
            "grid_cell_id": cell,
            "aqi": round(aqi, 1),
            "wind_speed": round(np.random.uniform(0, 20), 1),
            "temp": round(np.random.uniform(10, 35), 1),
            "humidity": round(np.random.uniform(20, 90), 1),
            "traffic_index": round(np.random.uniform(0, 100), 1),
        })

df = pd.DataFrame(rows)
df.to_csv("data/feature_store.csv", index=False)
print(f"Generated {len(df)} rows across {N_CELLS} cells and {N_DAYS} days")
print(df.head())