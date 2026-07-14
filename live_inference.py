import os
import sys
import json
import requests
import datetime
import pandas as pd
import numpy as np
import joblib

# Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_MODEL_DIR = os.path.join(BASE_DIR, "ai_model")

# Inject ai_model into sys.path to import idw correctly
sys.path.insert(0, AI_MODEL_DIR)
try:
    from interpolation import idw
except ImportError:
    print("Could not import idw from ai_model/interpolation.py. Make sure you are running from the project root.")
    sys.exit(1)

GRID_PATH = os.path.join(BASE_DIR, "backend", "static", "ahmedabad_1km_grid.geojson")
SENSORS_CSV = os.path.join(AI_MODEL_DIR, "data", "sensor_locations.csv")
MODELS_DIR = os.path.join(AI_MODEL_DIR, "models")
FORECAST_OUTPUT = os.path.join(BASE_DIR, "backend", "forecast_demo.json")

# Station-specific pollution factors (same as training pipeline)
STATION_FACTOR = {
    "AMD_AIRPORT":    1.05, "AMD_BOPAL":      0.75, "AMD_CHANDKHEDA": 0.90,
    "AMD_GYASPUR":    1.30, "AMD_MANINAGAR":  1.10, "AMD_NAVRANGPURA":0.85,
    "AMD_PIRANA":     1.40, "AMD_RAIKHAD":    1.05, "AMD_RAKHIAL":    1.20,
    "AMD_SATELLITE":  0.80,
}

def get_live_data():
    """Fetches real-time AQI and past 24h history for Ahmedabad using Open-Meteo API"""
    print("🌐 Fetching live AQI & history from Open-Meteo API (Ahmedabad)...")
    lat, lon = 23.0225, 72.5714
    
    # Fetch past 1 day to calculate lags and rolling stats
    aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5,carbon_monoxide,nitrogen_dioxide,us_aqi&past_days=1&forecast_days=1"
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    
    try:
        response = requests.get(aqi_url)
        response.raise_for_status()
        aqi_res = response.json()
        
        w_response = requests.get(weather_url)
        w_response.raise_for_status()
        w_res = w_response.json()
    except Exception as e:
        print(f"Failed to fetch live data: {e}")
        sys.exit(1)
    
    df_aqi = pd.DataFrame(aqi_res['hourly'])
    df_aqi['time'] = pd.to_datetime(df_aqi['time'])
    
    # Find the data point corresponding to the current hour
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    
    df_aqi['time_diff'] = abs(df_aqi['time'] - current_hour)
    curr_idx = df_aqi['time_diff'].idxmin()
    
    # Extract the past 24 hours up to the current hour
    past_24h = df_aqi.iloc[curr_idx-24 : curr_idx+1].copy()
    
    current_aqi = past_24h['us_aqi'].iloc[-1]
    current_pm25 = past_24h['pm2_5'].iloc[-1]
    current_no2 = past_24h['nitrogen_dioxide'].iloc[-1]
    current_co = past_24h['carbon_monoxide'].iloc[-1] / 1000.0  # Convert to match Kaggle approx scales
    
    # Calculate Lag Features
    hist_aqi = past_24h['us_aqi'].values
    
    aqi_lag_3h = hist_aqi[-4] if len(hist_aqi) >= 4 else current_aqi
    aqi_lag_6h = hist_aqi[-7] if len(hist_aqi) >= 7 else current_aqi
    aqi_lag_24h = hist_aqi[-25] if len(hist_aqi) >= 25 else current_aqi
    
    aqi_roll_mean_24h = np.mean(hist_aqi[-24:]) if len(hist_aqi) >= 24 else current_aqi
    aqi_roll_std_24h = np.std(hist_aqi[-24:]) if len(hist_aqi) >= 24 else 0
    aqi_trend_6h = current_aqi - aqi_lag_6h
    
    current_temp = w_res['current']['temperature_2m']
    current_humidity = w_res['current']['relative_humidity_2m']
    current_wind = w_res['current']['wind_speed_10m']
    
    print(f"✅ Live Data Acquired | Current AQI: {current_aqi:.1f} | PM2.5: {current_pm25} | 24h Avg: {aqi_roll_mean_24h:.1f}")
    
    return {
        "aqi": current_aqi, "pm25": current_pm25, "no2": current_no2, "co": current_co,
        "temp": current_temp, "humidity": current_humidity, "wind_speed": current_wind,
        "aqi_lag_3h": aqi_lag_3h, "aqi_lag_6h": aqi_lag_6h, "aqi_lag_24h": aqi_lag_24h,
        "aqi_roll_mean_24h": aqi_roll_mean_24h, "aqi_roll_std_24h": aqi_roll_std_24h,
        "aqi_trend_6h": aqi_trend_6h,
        "timestamp": current_hour
    }

def build_grid_features(live):
    """Interpolates the single live reading to 502 grid cells and adds time/traffic features"""
    print("🗺️ Building 1km spatial grid features (IDW Interpolation)...")
    with open(GRID_PATH) as f:
        geojson = json.load(f)
    
    grid = pd.DataFrame([{
        "grid_cell_id": feat["properties"]["grid_id"],
        "centroid_lat": feat["properties"]["centroid_lat"],
        "centroid_lon": feat["properties"]["centroid_lon"],
    } for feat in geojson["features"]])
    
    sensors = pd.read_csv(SENSORS_CSV)
    
    # Interpolate AQI based on station factors
    sensors["value"] = [live["aqi"] * STATION_FACTOR.get(sid, 1.0) for sid in sensors["station_id"]]
    grid_aqi = idw(
        sensors["lat"], sensors["lon"], sensors["value"],
        grid["centroid_lat"], grid["centroid_lon"], power=2.0
    )
    
    df = pd.DataFrame({"grid_cell_id": grid["grid_cell_id"]})
    
    # Distribute pollutants proportionally
    ratio = grid_aqi / max(live["aqi"], 1)
    df["pm25"] = live["pm25"] * ratio
    df["no2"] = live["no2"] * ratio
    df["co"] = live["co"] * ratio
    df["temp"] = live["temp"]
    df["humidity"] = live["humidity"]
    df["wind_speed"] = live["wind_speed"]
    
    # Time features
    ts = pd.to_datetime(live["timestamp"])
    df["hour"] = ts.hour
    df["dow"] = ts.dayofweek
    df["hour_sin"] = np.sin(2 * np.pi * ts.hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * ts.hour / 24.0)
    df["dow_sin"] = np.sin(2 * np.pi * ts.dayofweek / 7.0)
    df["dow_cos"] = np.cos(2 * np.pi * ts.dayofweek / 7.0)
    df["month"] = ts.month
    df["is_weekend"] = int(ts.dayofweek >= 5)
    
    # Constants
    df["is_public_holiday"] = 0
    df["is_crop_burning_season"] = int(ts.month in [10, 11])
    df["is_diwali_window"] = 0 
    
    # Traffic
    WEEKDAY = [0.10,0.05,0.05,0.05,0.10,0.20,0.40,0.70,0.90,1.00,
               0.80,0.70,0.70,0.70,0.65,0.70,0.80,0.95,1.00,0.95,
               0.80,0.60,0.40,0.20]
    df["traffic_index"] = WEEKDAY[ts.hour] * (0.6 if ts.dayofweek >= 5 else 1.0)
    
    # Spatial Lags
    df["aqi_lag_3h"] = live["aqi_lag_3h"] * ratio
    df["aqi_lag_6h"] = live["aqi_lag_6h"] * ratio
    df["aqi_lag_24h"] = live["aqi_lag_24h"] * ratio
    df["aqi_roll_mean_24h"] = live["aqi_roll_mean_24h"] * ratio
    df["aqi_roll_std_24h"] = live["aqi_roll_std_24h"] * ratio
    df["aqi_trend_6h"] = live["aqi_trend_6h"] * ratio
    
    # Hackathon Trick: The "Trend Multiplier"
    # If live 24h rolling average > 150, boost predictions by 20% to account for 2026 extremes
    calibration_multiplier = 1.2 if live["aqi_roll_mean_24h"] > 150 else 1.0
    
    if calibration_multiplier > 1.0:
        print("High Pollution Detected! Applying 1.2x Trend Multiplier to offset historical bounds.")
        
    # Save the base map data for /maps/getPollution
    pollution_csv_path = os.path.join(AI_MODEL_DIR, "data", "grid_pollution_demo.csv")
    csv_df = pd.DataFrame({
        "datetime": ts.isoformat(),
        "grid_id": grid["grid_cell_id"],
        "centroid_lat": grid["centroid_lat"],
        "centroid_lon": grid["centroid_lon"],
        "value": np.round(grid_aqi, 1)
    })
    csv_df.to_csv(pollution_csv_path, index=False)
    print(f"Updated base map: {pollution_csv_path}")
        
    return df, ts, calibration_multiplier

def run_inference():
    print(f"\nStarting Live Inference Pipeline")
    live = get_live_data()
    df, current_ts, multiplier = build_grid_features(live)
    
    FEATURE_COLUMNS = [
        "wind_speed", "temp", "humidity", "traffic_index",
        "hour", "dow", "hour_sin", "hour_cos", "dow_sin", "dow_cos",
        "is_public_holiday", "is_weekend", "month",
        "is_crop_burning_season", "is_diwali_window",
        "aqi_lag_3h", "aqi_lag_6h", "aqi_lag_24h",
        "aqi_roll_mean_24h", "aqi_roll_std_24h", "aqi_trend_6h",
    ]
    
    X = df[FEATURE_COLUMNS]
    forecast = {}
    
    print("Running LightGBM Models for 24h, 48h, and 72h horizons")
    for h in [24, 48, 72]:
        model_path = os.path.join(MODELS_DIR, f"model_{h}h.pkl")
        if not os.path.exists(model_path):
            print(f"Model not found: {model_path}. You must run ai_model/train.py first!")
            return
            
        model = joblib.load(model_path)
        preds = model.predict(X)
        
        # Apply the trend multiplier and ensure non-negative
        preds = np.clip(preds * multiplier, 0, None)
        df[f"forecast_{h}h"] = preds
    
    # Serialize to JSON format matching forecast_demo.json
    for _, row in df.iterrows():
        cell_id = row["grid_cell_id"]
        forecast[cell_id] = [
            {"hour": 24, "aqi": round(row["forecast_24h"])},
            {"hour": 48, "aqi": round(row["forecast_48h"])},
            {"hour": 72, "aqi": round(row["forecast_72h"])},
        ]
        
    forecast["_metadata"] = {
        "generated_at": current_ts.isoformat(),
        "is_live": True,
        "calibration_multiplier_applied": multiplier
    }
    
    # Save the file - Backend will serve this directly!
    with open(FORECAST_OUTPUT, "w") as f:
        json.dump(forecast, f)
        
    print(f"SUCCESS! Live forecast generated for {len(df)} grid cells.")
    print(f"Updated file: {FORECAST_OUTPUT}")
    print("\nTo see the live predictions in action, just run:")
    print("   Terminal 1: cd backend && uv run fastapi dev main.py")
    print("   Terminal 2: cd frontend && npm run dev\n")

if __name__ == "__main__":
    run_inference()
