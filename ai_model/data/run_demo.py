import pandas as pd
from advisor import detect_events, recommend

def test_pipeline():
    print("--- Simulating Forecast Data ---")
    now = pd.Timestamp.now(tz="Asia/Kolkata")
    
    # Create fake timeline data for two locations
    # Cell 101 spikes to Severe (350 AQI) 40 hours from now
    data = [
        {"cell_id": "Cell_101", "datetime": now + pd.Timedelta(hours=12), "pred_aqi": 120, "lat": 28.6, "lon": 77.2, "confidence": 0.9},
        {"cell_id": "Cell_101", "datetime": now + pd.Timedelta(hours=40), "pred_aqi": 350, "lat": 28.6, "lon": 77.2, "confidence": 0.85},
        {"cell_id": "Cell_102", "datetime": now + pd.Timedelta(hours=24), "pred_aqi": 45,  "lat": 28.7, "lon": 77.3, "confidence": 0.95}
    ]
    
    forecast_df = pd.DataFrame(data)
    
    print("\n1. Running Trigger Detection...")
    events = detect_events(forecast_df, now)
    print(f"Detected Events: {len(events)}")
    for ev in events:
        print(f" -> Cell {ev['cell_id']} crosses into {ev['category']} status in {ev['lead_time_hours']} hours.")

    print("\n2. Dispatching to Recommendation Layer...")
    recs = recommend(events)
    
    print("\n--- Final JSON Output For Frontend ---")
    import json
    print(json.dumps(recs, indent=2))

if __name__ == "__main__":
    test_pipeline()