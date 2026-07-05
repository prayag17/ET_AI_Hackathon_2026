import os, pandas as pd

# same points as your other pulls (grid-cell centroids or station coords)
points = pd.DataFrame({
    "cell_id": ["c001", "c002", "c003"],
    "lat":     [28.63, 28.70, 28.55],
    "lon":     [77.22, 77.10, 77.25],
    "road_density": [1.0, 0.6, 0.8],     # 0-1; leave all 1.0 if you skip the OSM step
})

hours = pd.date_range("2023-01-01", "2025-01-05 23:00", freq="h", tz="Asia/Kolkata")

# typical Delhi diurnal congestion curve (0-1): morning + evening rush peaks
WEEKDAY = [0.10,0.05,0.05,0.05,0.10,0.20,0.40,0.70,0.90,1.00,0.80,0.70,
           0.70,0.70,0.65,0.70,0.80,0.95,1.00,0.95,0.80,0.60,0.40,0.20]
def factor(ts):
    base = WEEKDAY[ts.hour]
    return base * (0.6 if ts.dayofweek >= 5 else 1.0)   # weekends lighter/flatter

tf = pd.DataFrame({"datetime": hours, "time_factor": [factor(t) for t in hours]})

traffic = points.merge(tf, how="cross")                 # points x hours
traffic["traffic_index"] = (traffic["road_density"] * traffic["time_factor"]).round(3)

os.makedirs("features", exist_ok=True)
traffic[["cell_id","lat","lon","datetime","traffic_index"]].to_csv(
    "features/traffic.csv", index=False)
print(f"Saved {len(traffic)} rows -> features/traffic.csv")