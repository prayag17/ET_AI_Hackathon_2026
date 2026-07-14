import os, requests, pandas as pd

HOURLY = ("temperature_2m,relative_humidity_2m,wind_speed_10m,"
          "wind_direction_10m,precipitation,boundary_layer_height")

def fetch_weather(lat, lon, start=None, end=None, forecast=False):
    if forecast:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "hourly": HOURLY,
                  "forecast_days": 3, "timezone": "Asia/Kolkata"}
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {"latitude": lat, "longitude": lon, "hourly": HOURLY,
                  "start_date": start, "end_date": end, "timezone": "Asia/Kolkata"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df["lat"], df["lon"] = lat, lon
    return df

os.makedirs("features", exist_ok=True)
points = [(23.03, 72.58)]  # Ahmedabad center

# history → training
hist = pd.concat([fetch_weather(la, lo, start="2024-01-01", end="2025-12-31")
                  for la, lo in points], ignore_index=True)
hist.to_csv("features/weather_history.csv", index=False)

# 72h forecast → inference
fut = pd.concat([fetch_weather(la, lo, forecast=True) for la, lo in points],
                ignore_index=True)
fut.to_csv("features/weather_forecast.csv", index=False)