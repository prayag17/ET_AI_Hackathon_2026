import pandas as pd

def load_data():
    df = pd.read_csv("data/feature_store.csv", parse_dates=["timestamp"])
    df = df.sort_values(["grid_cell_id", "timestamp"]).reset_index(drop=True)
    return df

def add_baselines(df, horizon_hours):
    """
    For a given horizon (24, 48, or 72), adds two columns:
    - persistence_pred_{h}h
    - seasonal_pred_{h}h
    These represent: "if asked to predict AQI at time T+h,
    what would the dumb guess have been?"
    """
    df = df.copy()
    df = df.set_index(["grid_cell_id", "timestamp"])

    results = []
    for cell, group in df.groupby(level="grid_cell_id"):
        group = group.reset_index()
        group = group.set_index("timestamp")

        persistence = group["aqi"].reindex(
            group.index - pd.Timedelta(hours=horizon_hours)
        ).values

        group[f"persistence_pred_{horizon_hours}h"] = group["aqi"].shift(horizon_hours)

        group[f"seasonal_pred_{horizon_hours}h"] = group["aqi"].shift(168)

        group["grid_cell_id"] = cell
        results.append(group.reset_index())

    return pd.concat(results, ignore_index=True)

if __name__ == "__main__":
    df = load_data()

    for h in [24, 48, 72]:
        df = add_baselines(df, h)

    df.to_csv("data/with_baselines.csv", index=False)
    print("Baselines added. Sample:")
    print(df[["timestamp", "grid_cell_id", "aqi", "persistence_pred_24h", "seasonal_pred_24h"]].dropna().head())