# pollution_event_calender.py
# Regenerates calendar to cover 2015-2020 (matching city_hour.csv dates)
# Run from ai_model/ folder:  python data/pollution_event_calender.py

import pandas as pd
import holidays

dates = pd.date_range(start='2015-01-01', end='2020-12-31')
df = pd.DataFrame({'date': dates})
indian_holidays = holidays.India(years=range(2015, 2021))

df["is_public_holiday"]     = df["date"].isin(indian_holidays).astype(int)
df["is_weekend"]            = (df["date"].dt.dayofweek >= 5).astype(int)
df["day_of_week"]           = df["date"].dt.dayofweek
df["month"]                 = df["date"].dt.month
df["is_crop_burning_season"] = df["date"].apply(
    lambda d: int((d.month == 10 and d.day >= 15) or (d.month == 11 and d.day <= 20))
)

diwali = {
    2015: "2015-11-11", 2016: "2016-10-30", 2017: "2017-10-19",
    2018: "2018-11-07", 2019: "2019-10-27", 2020: "2020-11-14"
}
windows = pd.to_datetime(list(diwali.values()))
df["is_diwali_window"] = df["date"].apply(
    lambda d: int(any(abs((d - w).days) <= 3 for w in windows))
)

df.to_csv("data/pollution_event_calendar.csv", index=False)
print(f"✅ Calendar saved: {df['date'].min().date()} -> {df['date'].max().date()}")
print(f"   {len(df)} days | {df['is_public_holiday'].sum()} holidays | {df['is_diwali_window'].sum()} Diwali window days")