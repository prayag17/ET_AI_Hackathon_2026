# wind_signal.py — issue #40: wind-based pollution-spread signal
#
# Adds a simple ventilation signal to the feature table:
#     ventilation_index = mixing height (proxy) x wind speed
#
# Mixing height isn't observed directly, so it's approximated from what the
# feature store already has: a diurnal convective term (the boundary layer
# grows through the day, collapses at night) scaled by temperature. Low
# ventilation = pollution has nowhere to go, so it accumulates; high
# ventilation = it disperses. The IMD/CPCB convention flags "poor
# ventilation" below ~6000 m^2/s, which becomes a binary feature too.
#
# NOTE ON SPREAD-TO-NEIGHBOURS: features_ready.csv uses synthetic cell ids
# (cell_000...) with no coordinates, so a directional advection feature
# (upwind neighbour AQI) can't be computed here. The ventilation form asked
# for in the issue is computable, and it's what this module implements.
#
# HOW TO RUN (A/B evaluation, decides whether the signal earns its place):
#   python wind_signal.py
#
# It trains the same LightGBM config grid as train.py twice per horizon —
# once with the base features, once with base + wind — on the same
# time-respecting split, and prints the RMSE comparison.
#
# RECORDED RESULT (2026-07-14, features_ready.csv @ 70,800 rows):
#   24h  base 15.543 -> base+wind 15.552  (+0.009, worse)
#   48h  base 15.532 -> base+wind 15.532  (-0.001, noise)
#   72h  base 15.516 -> base+wind 15.503  (-0.013, noise)
# All deltas are <0.1% of the baseline RMSE — the signal does NOT
# meaningfully improve the score, so per the issue it is NOT added to
# train.py's FEATURE_COLUMNS. (The AQI lag/rolling features already carry
# most of the dispersion information on this dataset; poor_ventilation is
# also nearly constant here at 99.2% positive.) The signal stays available
# in this module if richer weather data ever makes it worth re-testing.

import numpy as np
import pandas as pd

WIND_FEATURES = [
    "mixing_height_proxy",
    "ventilation_index",
    "poor_ventilation",
]


def add_wind_signal(df: pd.DataFrame) -> pd.DataFrame:
    """Derive the ventilation features from wind_speed / temp / hour."""
    df = df.copy()

    # wind_speed arrives in km/h (open-meteo wind_speed_10m) -> m/s
    wind_ms = df["wind_speed"] / 3.6

    # Convective mixing-height proxy:
    #   * ~150 m stable nocturnal layer as the floor
    #   * daytime growth follows a half-sine between 06:00 and 18:00
    #   * hotter days convect deeper (scaled by temperature)
    conv = np.sin(np.pi * (df["hour"] - 6) / 12).clip(lower=0)
    temp_scale = ((df["temp"] - 5) / 30).clip(0.2, 1.2)
    df["mixing_height_proxy"] = 150 + 1350 * conv * temp_scale

    df["ventilation_index"] = df["mixing_height_proxy"] * wind_ms
    df["poor_ventilation"] = (df["ventilation_index"] < 6000).astype(int)
    return df


if __name__ == "__main__":
    import lightgbm as lgb

    # Mirrors train.py (not imported — importing train.py runs its pipeline)
    BASE_FEATURES = [
        "wind_speed", "temp", "humidity", "traffic_index",
        "hour", "dow", "hour_sin", "hour_cos", "dow_sin", "dow_cos",
        "is_public_holiday", "is_weekend", "month",
        "is_crop_burning_season", "is_diwali_window",
        "aqi_lag_3h", "aqi_lag_6h", "aqi_lag_24h",
        "aqi_roll_mean_24h", "aqi_roll_std_24h", "aqi_trend_6h",
    ]
    PARAM_GRID = [
        {"num_leaves": 15,  "learning_rate": 0.10, "n_estimators": 100},
        {"num_leaves": 31,  "learning_rate": 0.05, "n_estimators": 200},
        {"num_leaves": 63,  "learning_rate": 0.03, "n_estimators": 400},
        {"num_leaves": 127, "learning_rate": 0.02, "n_estimators": 600},
    ]

    print("Loading data/features_ready.csv...")
    df = pd.read_csv("data/features_ready.csv", parse_dates=["timestamp"])
    df = add_wind_signal(df)
    print(f"Loaded {len(df)} rows | poor-ventilation share: "
          f"{df['poor_ventilation'].mean():.1%}")

    # Same target construction + time split as train.py
    frames = []
    for _, group in df.groupby("grid_cell_id"):
        group = group.sort_values("timestamp").copy()
        for h in (24, 48, 72):
            group[f"target_{h}h"] = group["aqi"].shift(-h)
        frames.append(group)
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]

    def best_rmse(feature_cols, horizon):
        tcol = f"target_{horizon}h"
        tr = train_df.dropna(subset=[tcol])
        te = test_df.dropna(subset=[tcol])
        best = float("inf")
        for cfg in PARAM_GRID:
            model = lgb.LGBMRegressor(**cfg, verbose=-1)
            model.fit(tr[feature_cols], tr[tcol])
            preds = model.predict(te[feature_cols])
            rmse = float(np.sqrt(np.mean((te[tcol].values - preds) ** 2)))
            best = min(best, rmse)
        return best

    # A horizon only counts as a win if the improvement is meaningful —
    # at least 0.2% of the baseline RMSE, not just float noise.
    MIN_REL_GAIN = 0.002

    print("\n" + "=" * 60)
    print(f"{'Horizon':<10}{'base RMSE':>12}{'base+wind RMSE':>17}{'delta':>10}")
    print("=" * 60)
    wins = 0
    for h in (24, 48, 72):
        base = best_rmse(BASE_FEATURES, h)
        wind = best_rmse(BASE_FEATURES + WIND_FEATURES, h)
        delta = wind - base
        meaningful = delta < -MIN_REL_GAIN * base
        if meaningful:
            wins += 1
        print(f"{h}h{'':<7}{base:>12.3f}{wind:>17.3f}{delta:>+10.3f}"
              f"  {'improves' if meaningful else 'no meaningful gain'}")
    print("=" * 60)
    if wins >= 2:
        print("VERDICT: wind signal meaningfully helps on most horizons — "
              "keep it (add WIND_FEATURES to train.py's FEATURE_COLUMNS).")
    else:
        print("VERDICT: wind signal does not earn its place — leave "
              "train.py unchanged (issue #40 allows dropping it).")
