import pandas as pd
import numpy as np

def rmse(actual, predicted):
    mask = ~(actual.isna() | predicted.isna())
    actual, predicted = actual[mask], predicted[mask]
    if len(actual) == 0:
        return None
    return np.sqrt(np.mean((actual - predicted) ** 2))

def skill_score(model_rmse, baseline_rmse):
    if model_rmse is None or baseline_rmse is None or baseline_rmse == 0:
        return None
    return 1 - (model_rmse / baseline_rmse)

def print_scorecard(df, model_pred_col_template="model_pred_{h}h"):

    print(f"{'Horizon':<10}{'Baseline':<12}{'Persist RMSE':<15}"
          f"{'Seasonal RMSE':<15}{'Model RMSE':<14}{'Skill score':<12}")
    print("-" * 80)

    for h in [24, 48, 72]:
        actual = df["aqi"]
        persist_pred = df[f"persistence_pred_{h}h"]
        seasonal_pred = df[f"seasonal_pred_{h}h"]

        persist_rmse = rmse(actual, persist_pred)
        seasonal_rmse = rmse(actual, seasonal_pred)

        best_baseline_rmse = min(
            x for x in [persist_rmse, seasonal_rmse] if x is not None
        )

        model_col = model_pred_col_template.format(h=h)
        if model_col in df.columns:
            model_rmse = rmse(actual, df[model_col])
            skill = skill_score(model_rmse, best_baseline_rmse)
            model_str = f"{model_rmse:.1f}"
            skill_str = f"{skill:+.2f}" if skill is not None else "n/a"
        else:
            model_str = "not built yet"
            skill_str = "n/a"

        print(f"{h}h{'':<7}{best_baseline_rmse:<12.1f}"
              f"{persist_rmse:<15.1f}{seasonal_rmse:<15.1f}"
              f"{model_str:<14}{skill_str:<12}")

if __name__ == "__main__":
    df = pd.read_csv("data/with_baselines.csv", parse_dates=["timestamp"])
    print_scorecard(df)