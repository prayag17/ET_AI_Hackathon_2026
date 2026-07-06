import pandas as pd
import numpy as np

def rmse(actual, predicted):
    """Root Mean Squared Error — lower is better."""
    mask = ~(actual.isna() | predicted.isna())
    a, p = actual[mask], predicted[mask]
    if len(a) == 0:
        return None
    return np.sqrt(np.mean((a - p) ** 2))

def mae(actual, predicted):
    """Mean Absolute Error easier to interpret than RMSE (same units as AQI)."""
    mask = ~(actual.isna() | predicted.isna())
    a, p = actual[mask], predicted[mask]
    if len(a) == 0:
        return None
    return np.mean(np.abs(a - p))

def skill_score(model_rmse, baseline_rmse):

    if model_rmse is None or baseline_rmse is None or baseline_rmse == 0:
        return None
    return 1 - (model_rmse / baseline_rmse)


def print_scorecard(df):
    print("\n" + "=" * 85)
    print("AQI FORECAST MODEL SCORECARD")
    print("=" * 85)
    print(f"{'Horizon':<10} {'Persist RMSE':<15} {'Seasonal RMSE':<16} "
          f"{'Best baseline':<16} {'Model RMSE':<13} {'Skill score':<14} {'Result'}")
    print("-" * 85)

    all_positive = True

    for h in [24, 48, 72]:
        actual       = df["aqi"]
        persist_col  = f"persistence_pred_{h}h"
        seasonal_col = f"seasonal_pred_{h}h"
        model_col    = f"model_pred_{h}h"

        persist_rmse  = rmse(actual, df[persist_col])
        seasonal_rmse = rmse(actual, df[seasonal_col])

        valid_baselines = [x for x in [persist_rmse, seasonal_rmse] if x is not None]
        if not valid_baselines:
            print(f"{h}h{'':6} — baseline columns missing")
            continue
        best_baseline = min(valid_baselines)

        if model_col in df.columns:
            model_rmse_val = rmse(actual, df[model_col])
            skill          = skill_score(model_rmse_val, best_baseline)
            model_str      = f"{model_rmse_val:.2f}"
            skill_str      = f"{skill:+.3f}" if skill is not None else "—"

            if skill is not None and skill > 0:
                result = "✅ beating baseline"
            else:
                result = "❌ not beating baseline"
                all_positive = False
        else:
            model_rmse_val = None
            model_str      = "not trained yet"
            skill_str      = "—"
            result         = "⏳ run train.py first"
            all_positive   = False

        print(f"{h}h{'':7} "f"{persist_rmse:<15.2f} "f"{seasonal_rmse:<16.2f} "f"{best_baseline:<16.2f} "f"{model_str:<13} "f"{skill_str:<14} "f"{result}")

    print("=" * 85)

    if all_positive:
        print("🎉 All horizons beating baseline — issue #35 and #38 DONE")
    else:
        print("⚠️  Some horizons not beating baseline.")
        print("   → Try adding the 'deep' config to PARAM_GRID in train.py and rerun.")
    print()


def print_mae_breakdown(df):
    print("MAE BREAKDOWN  (easier to explain: 'average prediction error in AQI units')")
    print("-" * 50)
    for h in [24, 48, 72]:
        model_col = f"model_pred_{h}h"
        if model_col in df.columns:
            mae_val = mae(df["aqi"], df[model_col])
            if mae_val is not None:
                print(f"  {h}h  average error = {mae_val:.1f} AQI units")
    print()

def print_feature_importance():
    try:
        import joblib
        from train import FEATURE_COLUMNS

        print("TOP 10 FEATURES  (what the model relies on most)")
        print("-" * 50)
        for h in [24, 48, 72]:
            model = joblib.load(f"models/model_{h}h.pkl")
            importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
            top10 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  {h}h: " + ", ".join(f"{k}({v:.0f})" for k, v in top10))
        print()
    except FileNotFoundError:
        pass   

if __name__ == "__main__":
    # Step 1: load baseline file
    print("Loading data/with_baselines.csv...")
    df = pd.read_csv("data/with_baselines.csv", parse_dates=["timestamp"])
    print(f"Loaded: {len(df)} rows")

    # Step 2: merge model predictions if they exist
    try:
        preds = pd.read_csv("data/model_predictions.csv", parse_dates=["timestamp"])
        df = df.merge(
            preds[["timestamp", "grid_cell_id",
                   "model_pred_24h", "model_pred_48h", "model_pred_72h"]],
            on=["timestamp", "grid_cell_id"],
            how="left"
        )
        print("Model predictions merged.")
    except FileNotFoundError:
        print("No model predictions found — run train.py first for full scorecard.")

    # Step 3: print everything
    print_scorecard(df)
    print_mae_breakdown(df)
    print_feature_importance()