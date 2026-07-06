import pandas as pd
import numpy as np
import joblib



# Do NOT change this list unless you retrain 
FEATURE_COLUMNS = [
    "pm25",
    "no2",
    "co",
    "traffic_index",
    "hour",
    "dow",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "is_public_holiday",
    "is_weekend",
    "month",
    "is_crop_burning_season",
    "is_diwali_window",
    "aqi_lag_3h",
    "aqi_lag_6h",
    "aqi_lag_24h",
    "aqi_roll_mean_24h",
    "aqi_roll_std_24h",
    "aqi_trend_6h",
]

# Cache ,models are loaded from disk once, then kept in memory
_models = {}


def _load_models():
    global _models
    if not _models:
        for h in [24, 48, 72]:
            path = f"models/model_{h}h.pkl"
            try:
                _models[h] = joblib.load(path)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Model not found: {path}\n"
                    f"Run train.py first."
                )
    return _models


def get_city_forecast(features_path="data/features_ready.csv"):
    """
    Returns full city-wide forecast for all 502 grid cells at 24h, 48h, 72h.

    Parameters
    ----------
    features_path : str
        Path to features_ready.csv

    Returns
    -------
    pd.DataFrame with columns:
        grid_cell_id            — AHM-0001 format, matches GeoJSON
        horizon_hours           — 24, 48, or 72
        predicted_aqi           — forecasted AQI value (rounded to 1 decimal)
        forecast_for_timestamp  — the future timestamp this prediction is for
        base_timestamp          — the most recent timestamp in the data
    """
    models = _load_models()


    df = pd.read_csv(features_path, parse_dates=["timestamp"])

    # Verify all feature columns exist
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns in {features_path}: {missing}\n"
            f"Available: {list(df.columns)}"
        )

    # Take the most recent row per cell — that's the "now" snapshot to forecast from
    latest = (
        df.sort_values("timestamp")
          .groupby("grid_cell_id")
          .tail(1)
          .reset_index(drop=True)
    )

    results = []
    for h, model in models.items():
        preds = model.predict(latest[FEATURE_COLUMNS])

        for i, (_, row) in enumerate(latest.iterrows()):
            results.append({
                "grid_cell_id":           row["grid_cell_id"],
                "horizon_hours":          h,
                "predicted_aqi":          round(float(preds[i]), 1),
                "forecast_for_timestamp": row["timestamp"] + pd.Timedelta(hours=h),
                "base_timestamp":         row["timestamp"],
            })

    forecast_df = (
        pd.DataFrame(results)
          .sort_values(["grid_cell_id", "horizon_hours"])
          .reset_index(drop=True)
    )
    return forecast_df


def get_cell_forecast(cell_id, features_path="data/features_ready.csv"):
    """
    Forecast for a single grid cell.
    Used by the dashboard when a user clicks one cell on the map.

    Returns
    -------
    dict: {cell_id, base_timestamp, forecasts: [{horizon_hours, predicted_aqi, timestamp}]}
    """
    full = get_city_forecast(features_path)
    cell_df = full[full["grid_cell_id"] == cell_id]

    if cell_df.empty:
        raise ValueError(
            f"Cell '{cell_id}' not found.\n"
            f"Valid example: {full['grid_cell_id'].iloc[0]}"
        )

    return {
        "cell_id":        cell_id,
        "base_timestamp": cell_df["base_timestamp"].iloc[0].isoformat(),
        "forecasts": [
            {
                "horizon_hours": int(row["horizon_hours"]),
                "predicted_aqi": row["predicted_aqi"],
                "forecast_for_timestamp": row["forecast_for_timestamp"].isoformat(),
            }
            for _, row in cell_df.iterrows()
        ]
    }


def get_forecast_as_grid(features_path="data/features_ready.csv"):
    """
    Wide-format forecast — one row per cell, columns pred_24h/pred_48h/pred_72h.
    This is the format the map dashboard needs to colour each grid cell.

    Returns
    -------
    pd.DataFrame: grid_cell_id, pred_24h, pred_48h, pred_72h
    """
    full = get_city_forecast(features_path)
    wide = full.pivot(
        index="grid_cell_id",
        columns="horizon_hours",
        values="predicted_aqi"
    ).reset_index()
    wide.columns = ["grid_cell_id", "pred_24h", "pred_48h", "pred_72h"]
    return wide


if __name__ == "__main__":
    print("Testing predict.py...\n")

    try:
        # Test 1: full city forecast
        print("1. get_city_forecast()")
        forecast = get_city_forecast()
        n_cells = forecast["grid_cell_id"].nunique()
        print(f"    {len(forecast)} rows | {n_cells} cells | 3 horizons")
        print(f"   Sample cell IDs: {forecast['grid_cell_id'].unique()[:3].tolist()}")
        print(f"   AQI range: {forecast['predicted_aqi'].min():.0f} – {forecast['predicted_aqi'].max():.0f}")
        print()

        # Test 2: single cell
        sample_cell = forecast["grid_cell_id"].iloc[0]
        print(f"2. get_cell_forecast('{sample_cell}')")
        single = get_cell_forecast(sample_cell)
        for f in single["forecasts"]:
            print(f"   {f['horizon_hours']}h → AQI {f['predicted_aqi']} at {f['forecast_for_timestamp']}")
        print()

        # Test 3: grid format for map
        print("3. get_forecast_as_grid()")
        grid = get_forecast_as_grid()
        print(f"   {len(grid)} cells")
        print(f"   Columns: {list(grid.columns)}")
        print()
        print(grid.head(5).to_string(index=False))

    except FileNotFoundError as e:
        print(f"{e}")