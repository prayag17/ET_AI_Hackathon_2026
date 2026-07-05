# features.py
import pandas as pd
import numpy as np

def build_features(df, calendar_path="data/pollution_event_calendar.csv"):
    df = df.copy()
    df = df.sort_values(["grid_cell_id", "timestamp"]).reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["dow"]  = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"]  = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"]  = np.cos(2 * np.pi * df["dow"] / 7)

    cal = pd.read_csv(calendar_path, parse_dates=["date"])
    cal["date"] = cal["date"].dt.date
    df["date"] = df["timestamp"].dt.date
    df = df.merge(cal, on="date", how="left")
    df = df.drop(columns=["date", "day_of_week", "month_x"],errors="ignore")
    if "month_y" in df.columns:
        df = df.rename(columns={"month_y": "month"})


    feature_frames = []
    for cell, group in df.groupby("grid_cell_id"):
        group = group.sort_values("timestamp").copy()
        group["aqi_lag_3h"]       = group["aqi"].shift(3)
        group["aqi_lag_6h"]       = group["aqi"].shift(6)
        group["aqi_lag_24h"]      = group["aqi"].shift(24)
        group["aqi_roll_mean_24h"] = group["aqi"].shift(1).rolling(24).mean()
        group["aqi_roll_std_24h"]  = group["aqi"].shift(1).rolling(24).std()
        group["aqi_trend_6h"]      = (group["aqi"].shift(1) - group["aqi"].shift(6)) / 6
        feature_frames.append(group)

    df = pd.concat(feature_frames, ignore_index=True)

    return df

FEATURE_COLUMNS = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "aqi_lag_3h", "aqi_lag_6h", "aqi_lag_24h",
    "aqi_roll_mean_24h", "aqi_roll_std_24h", "aqi_trend_6h",
    "wind_speed",
    "temp",         
    "humidity",
    "traffic_index",
    "is_public_holiday", "is_weekend",
    "is_crop_burning_season", "is_diwali_window",
]

if __name__ == "__main__":
    df = pd.read_csv("data/feature_store.csv", parse_dates=["timestamp"])
    df = build_features(df, calendar_path="data/pollution_event_calendar.csv")
    df = df.dropna(subset=FEATURE_COLUMNS)
    df.to_csv("data/features_ready.csv", index=False)
    print(f"Done: {len(df)} rows, {len(FEATURE_COLUMNS)} features")
    print(df[["timestamp", "grid_cell_id"] + FEATURE_COLUMNS].head())