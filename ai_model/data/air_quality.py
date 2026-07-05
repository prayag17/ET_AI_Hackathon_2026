import os, time, requests, pandas as pd

API_KEY = os.environ["OPENAQ_API_KEY"]        # free key from https://explore.openaq.org
BASE    = "https://api.openaq.org/v3"
HEADERS = {"X-API-Key": API_KEY}

DELHI_BBOX = "76.84,28.40,77.35,28.88"         # xmin(lon),ymin(lat),xmax(lon),ymax(lat)
PM25 = 2                                        # OpenAQ parameter id for PM2.5

def get(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# 1) find Delhi stations that measure PM2.5
locs = get("/locations", {"bbox": DELHI_BBOX, "parameters_id": PM25, "limit": 1000})["results"]
print(f"Found {len(locs)} stations")

sensors = []
for loc in locs:
    for s in loc["sensors"]:
        if s["parameter"]["id"] == PM25:
            sensors.append({"sensor_id": s["id"], "station": loc["name"],
                            "lat": loc["coordinates"]["latitude"],
                            "lon": loc["coordinates"]["longitude"]})

# 2) HISTORY -> training labels (paginated hourly pull per sensor)
def pull_hours(sid, dt_from, dt_to):
    rows, page = [], 1
    while True:
        data = get(f"/sensors/{sid}/hours",
                   {"datetime_from": dt_from, "datetime_to": dt_to, "limit": 1000, "page": page})
        res = data["results"]
        rows += res
        if len(res) < 1000: break
        page += 1; time.sleep(0.2)             # be polite; avoid rate limits
    return rows

all_rows = []
for s in sensors:
    for h in pull_hours(s["sensor_id"], "2023-01-01", "2024-12-31"):
        all_rows.append({"station": s["station"], "lat": s["lat"], "lon": s["lon"],
                         "datetime": h["period"]["datetimeFrom"]["local"], "pm25": h["value"]})
    print(f"{s['station']}: done")

os.makedirs("features", exist_ok=True)
hist = pd.DataFrame(all_rows)
hist["datetime"] = pd.to_datetime(hist["datetime"])
hist = hist[(hist["pm25"] >= 0) & (hist["pm25"] < 1000)]   # drop garbage (negatives, 999s)
hist.to_csv("features/air_quality_history.csv", index=False)

# 3) LIVE -> latest reading per station (for inference / dashboard)
latest = get(f"/parameters/{PM25}/latest", {"limit": 1000})["results"]
ids = {s["sensor_id"] for s in sensors}
live = [{"sensor_id": r["sensorsId"], "datetime": r["datetime"]["local"], "pm25": r["value"]}
        for r in latest if r.get("sensorsId") in ids]
pd.DataFrame(live).to_csv("features/air_quality_live.csv", index=False)
print("Saved air_quality_history.csv and air_quality_live.csv")