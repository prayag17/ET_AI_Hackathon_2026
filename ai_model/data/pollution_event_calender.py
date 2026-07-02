import pandas as pd
import holidays

dates = pd.date_range(start='2023-01-01', end='2025-12-31')
df = pd.DataFrame({'date': dates})
indian_holidays = holidays.India(years=[2023, 2024, 2025])

df["is_public_holiday"] = df["date"].isin(indian_holidays).astype(int)
df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
df["day_of_week"] = df["date"].dt.dayofweek
df["month"] = df["date"].dt.month
df["is_crop_burning_season"] = df["date"].apply(
    lambda d: int((d.month == 10 and d.day >= 15)
                  or (d.month == 11 and d.day <= 20))
)
# Diwali windows — fill in the actual dates per year
diwali = {2023: "2023-11-12", 2024: "2024-11-01", 2025: "2025-10-20"}
windows = pd.to_datetime(list(diwali.values()))
df["is_diwali_window"] = df["date"].apply(
    lambda d: int(any(abs((d - w).days) <= 3 for w in windows))
)

df.to_csv("pollution_event_calendar.csv", index=False)
print("Pollution event calendar saved to pollution_event_calendar.csv")
