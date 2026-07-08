# features.py
import pandas as pd
import numpy as np

def build_features(df, calendar_path="data/pollution_event_calendar.csv"):
    df = df.copy()
    df = df.sort_values(["grid_cell_id", "timestamp"]).reset_index(drop=True)

<<<<<<< HEAD
    df["hour"] = df["timestamp"].dt.hour
    df["dow"]  = df["timestamp"].dt.dayofweek
=======
    # Time signals
    df["hour"]  = df["timestamp"].dt.hour
    df["dow"]   = df["timestamp"].dt.dayofweek
>>>>>>> df10704ebcf95f53795bcb41d20811040ef14c6c
    df["month"] = df["timestamp"].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"]  = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"]  = np.cos(2 * np.pi * df["dow"] / 7)

<<<<<<< HEAD
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

=======
    # Calendar join
    cal = pd.read_csv(calendar_path, parse_dates=["date"])
    cal["date"] = cal["date"].dt.date
    df["date"]  = df["timestamp"].dt.date
    df = df.merge(cal, on="date", how="left")
    df = df.drop(columns=["date", "day_of_week", "month_x"], errors="ignore")
    if "month_y" in df.columns:
        df = df.rename(columns={"month_y": "month"})

    # Fill calendar flags with 0 if date not in calendar
    for col in ["is_public_holiday","is_weekend","is_crop_burning_season","is_diwali_window"]:
        df[col] = df.get(col, 0).fillna(0).astype(int)

    # Lag and trend signals per cell
    frames = []
    for cell, group in df.groupby("grid_cell_id"):
        g = group.sort_values("timestamp").copy()
        g["aqi_lag_3h"]        = g["aqi"].shift(3)
        g["aqi_lag_6h"]        = g["aqi"].shift(6)
        g["aqi_lag_24h"]       = g["aqi"].shift(24)
        g["aqi_roll_mean_24h"] = g["aqi"].shift(1).rolling(24).mean()
        g["aqi_roll_std_24h"]  = g["aqi"].shift(1).rolling(24).std()
        g["aqi_trend_6h"]      = (g["aqi"].shift(1) - g["aqi"].shift(6)) / 6
        frames.append(g)

    df = pd.concat(frames, ignore_index=True)
    return df


# These are the exact columns train.py will use
>>>>>>> df10704ebcf95f53795bcb41d20811040ef14c6c
FEATURE_COLUMNS = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "aqi_lag_3h", "aqi_lag_6h", "aqi_lag_24h",
    "aqi_roll_mean_24h", "aqi_roll_std_24h", "aqi_trend_6h",
<<<<<<< HEAD
    "wind_speed",
    "temp",         
    "humidity",
    "traffic_index",
=======
    "pm25", "no2", "co", "traffic_index",
>>>>>>> df10704ebcf95f53795bcb41d20811040ef14c6c
    "is_public_holiday", "is_weekend",
    "is_crop_burning_season", "is_diwali_window",
]

<<<<<<< HEAD
if __name__ == "__main__":
    df = pd.read_csv("data/feature_store.csv", parse_dates=["timestamp"])
    df = build_features(df, calendar_path="data/pollution_event_calendar.csv")
    df = df.dropna(subset=FEATURE_COLUMNS)
    df.to_csv("data/features_ready.csv", index=False)
    print(f"Done: {len(df)} rows, {len(FEATURE_COLUMNS)} features")
    print(df[["timestamp", "grid_cell_id"] + FEATURE_COLUMNS].head())
=======

if __name__ == "__main__":
    print("Loading feature_store.csv...")
    df = pd.read_csv("data/feature_store.csv", parse_dates=["timestamp"])
    print(f"  {len(df):,} rows | {df['grid_cell_id'].nunique()} cells")
    print(f"  Columns: {list(df.columns)}")

    print("Building features...")
    df = build_features(df, calendar_path="data/pollution_event_calendar.csv")

    # Drop only rows where lag features are null (first 24h per cell — expected)
    lag_cols = ["aqi_lag_3h","aqi_lag_6h","aqi_lag_24h","aqi_roll_mean_24h","aqi_roll_std_24h"]
    before = len(df)
    df = df.dropna(subset=lag_cols)
    print(f"  Dropped {before - len(df):,} rows (first 24h per cell — expected)")

    df.to_csv("data/features_ready.csv", index=False)
    print(f"\n✅ Done: {len(df):,} rows | {len(FEATURE_COLUMNS)} feature columns")
    print(f"   Cells: {df['grid_cell_id'].nunique()}")
    missing = df[FEATURE_COLUMNS].isnull().sum()
    missing = missing[missing > 0]
    if len(missing) == 0:
        print("   No nulls in feature columns ✅")
    else:
        print("   Nulls remaining:", missing.to_dict())
>>>>>>> df10704ebcf95f53795bcb41d20811040ef14c6c
