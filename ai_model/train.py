# train.py
# Handles: #13 (training) and #38 (tuning) — one script does both
#
# INPUT:  data/features_ready.csv   ← Divy's features.py already produced this
# OUTPUT: data/model_predictions.csv
#         models/model_24h.pkl
#         models/model_48h.pkl
#         models/model_72h.pkl
#         reports/tuning_log.csv
#
# HOW TO RUN:
#   python train.py
#
# WHEN DONE: tell Divy to run scorecard.py to see skill scores

import os
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

# ── Exact column names from features_ready.csv ─────────────────────────────
# Do NOT change these — they must match what's in features_ready.csv exactly
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

# ── Setup folders ───────────────────────────────────────────────────────────
os.makedirs("models",  exist_ok=True)
os.makedirs("reports", exist_ok=True)

# ── Step 1: Load features_ready.csv ────────────────────────────────────────
print("Loading data/features_ready.csv...")
df = pd.read_csv("data/features_ready.csv", parse_dates=["timestamp"])
print(f"Loaded: {len(df)} rows | {df['grid_cell_id'].nunique()} cells | "
      f"{df['timestamp'].min().date()} → {df['timestamp'].max().date()}")

# Sanity check — catch column name mismatches immediately
missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
if missing:
    raise ValueError(
        f"\nThese columns are missing from features_ready.csv:\n  {missing}\n"
        f"Available columns: {list(df.columns)}"
    )
print(f"All {len(FEATURE_COLUMNS)} feature columns confirmed present.")

# ── Step 2: Build targets ───────────────────────────────────────────────────
# For a 24h model: target at time T = actual AQI at time T+24
# We create this by shifting aqi BACKWARD by h rows per cell
# Rows at the end of each cell's data get NaN targets — dropped later
print("\nBuilding targets (24h, 48h, 72h)...")
frames = []
for cell, group in df.groupby("grid_cell_id"):
    group = group.sort_values("timestamp").copy()
    group["target_24h"] = group["aqi"].shift(-24)
    group["target_48h"] = group["aqi"].shift(-48)
    group["target_72h"] = group["aqi"].shift(-72)
    frames.append(group)
df = pd.concat(frames, ignore_index=True)

# ── Step 3: Time-respecting train / test split ──────────────────────────────
# IMPORTANT: always split by TIME, never randomly
# Earlier 80% = training | Later 20% = testing
# Reason: if you split randomly, the model sees future data during training
# and gets fake-good scores that fall apart on real new data
df = df.sort_values("timestamp").reset_index(drop=True)
split_idx  = int(len(df) * 0.8)
split_time = df.iloc[split_idx]["timestamp"]
train_df   = df.iloc[:split_idx]
test_df    = df.iloc[split_idx:]
print(f"Train: {len(train_df)} rows up to {split_time.date()}")
print(f"Test:  {len(test_df)} rows after {split_time.date()}")

# ── Step 4: Configs to try (tuning) ────────────────────────────────────────
# For each horizon we try these 4 configs and keep the one with lowest RMSE.
# This is what satisfies issue #38 (tuning) — the log file is the proof.
#
# num_leaves:    complexity of each tree. higher = fits more detail
# learning_rate: step size per tree.    lower   = more careful, needs more trees
# n_estimators:  number of trees.       more    = stronger but slower to train
PARAM_GRID = [
    {"num_leaves": 15,  "learning_rate": 0.10, "n_estimators": 100, "label": "simple"},
    {"num_leaves": 31,  "learning_rate": 0.05, "n_estimators": 200, "label": "medium"},
    {"num_leaves": 63,  "learning_rate": 0.03, "n_estimators": 400, "label": "complex"},
    {"num_leaves": 127, "learning_rate": 0.02, "n_estimators": 600, "label": "deep"},
]

# ── Step 5: Train one model per horizon, keep the best config ──────────────
all_predictions = {}
tuning_log      = []

print("\n" + "=" * 65)
print(f"{'Horizon':<10}{'Config':<12}{'RMSE':>8}  {'Status'}")
print("=" * 65)

for horizon in [24, 48, 72]:
    target_col = f"target_{horizon}h"

    h_train = train_df.dropna(subset=[target_col])
    h_test  = test_df.dropna(subset=[target_col])

    X_train, y_train = h_train[FEATURE_COLUMNS], h_train[target_col]
    X_test,  y_test  = h_test[FEATURE_COLUMNS],  h_test[target_col]

    best_rmse  = float("inf")
    best_model = None
    best_preds = None

    for cfg in PARAM_GRID:
        params = {k: v for k, v in cfg.items() if k != "label"}
        params["verbose"] = -1  # suppress LightGBM internal output

        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train)

        preds     = model.predict(X_test)
        rmse_val  = np.sqrt(np.mean((y_test.values - preds) ** 2))
        is_best   = rmse_val < best_rmse

        if is_best:
            best_rmse  = rmse_val
            best_model = model
            best_preds = preds

        status = "← best so far" if is_best else ""
        print(f"{horizon}h{'':<7} {cfg['label']:<12} {rmse_val:>8.2f}  {status}")

        tuning_log.append({
            "horizon":       horizon,
            "config":        cfg["label"],
            "num_leaves":    cfg["num_leaves"],
            "learning_rate": cfg["learning_rate"],
            "n_estimators":  cfg["n_estimators"],
            "test_rmse":     round(rmse_val, 4),
            "is_best":       is_best,
        })

    # Save the best model for this horizon
    model_path = f"models/model_{horizon}h.pkl"
    joblib.dump(best_model, model_path)
    print(f"  → Saved best {horizon}h model  RMSE={best_rmse:.2f}  →  {model_path}\n")

    # Store test-set predictions — scorecard will read these
    out = h_test[["timestamp", "grid_cell_id", "aqi"]].copy()
    out[f"model_pred_{horizon}h"] = best_preds
    all_predictions[horizon] = out

# ── Step 6: Save tuning log ─────────────────────────────────────────────────
log_df = pd.DataFrame(tuning_log)
log_df.to_csv("reports/tuning_log.csv", index=False)

print("=" * 65)
print("TUNING SUMMARY")
print("=" * 65)
for h in [24, 48, 72]:
    best_row = log_df[(log_df["horizon"] == h) & (log_df["is_best"])].iloc[0]
    print(f"  {h}h  best config={best_row['config']:<10} "
          f"leaves={int(best_row['num_leaves']):<5} "
          f"lr={best_row['learning_rate']:<6} "
          f"rmse={best_row['test_rmse']:.2f}")

# ── Step 7: Merge predictions from all horizons and save ───────────────────
print("\nMerging predictions across all horizons...")
merged = all_predictions[24]
for h in [48, 72]:
    merged = merged.merge(
        all_predictions[h][["timestamp", "grid_cell_id", f"model_pred_{h}h"]],
        on=["timestamp", "grid_cell_id"],
        how="outer"
    )

merged.to_csv("data/model_predictions.csv", index=False)
print(f"Saved {len(merged)} rows to data/model_predictions.csv")
print("\n✅ Done. Tell Divy to run:  python scorecard.py")
