import os
import json
import logging
import pandas as pd
from openai import OpenAI  # OpenRouter uses the OpenAI library structure

# Configure logging to monitor fallback triggers
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Hardcoded constants for GRAP mapping
ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
BANDS = [
    (50, "Good"), (100, "Satisfactory"), (200, "Moderate"),
    (300, "Poor"), (400, "Very Poor"), (10000, "Severe")
]

GRAP = {
    "Poor": {
        "stage": "Stage I",
        "measures": [
            "Mechanized road sweeping + water sprinkling",
            "Strict dust control at construction sites",
            "Ban open waste/biomass burning"
        ]
    },
    "Very Poor": {
        "stage": "Stage II",
        "measures": [
            "Intensify sprinkling on hotspot roads",
            "Raise parking fees to cut private vehicle use",
            "Boost public transport frequency"
        ]
    },
    "Severe": {
        "stage": "Stage III",
        "measures": [
            "Halt non-essential construction & demolition",
            "Restrict older/higher-emission vehicles",
            "Close brick kilns and stone crushers"
        ]
    },
}

SYSTEM_PROMPT = """You are an air-quality response advisor for a city pollution board.
You get (1) forecast trigger events and (2) the official GRAP plan.
Write ONE recommendation per event. 

Rules:
- Only use measures from the GRAP list for that event's category. Never invent measures.
- Schedule the action to START before the spike, using lead_time_hours.
- One-sentence reason a busy official can act on.
- Never change the numbers you are given (aqi, times, confidence).

Return ONLY a JSON array. Each item must exactly match this JSON schema:
{
  "cell_id": "string",
  "action": "string",
  "grap_stage": "string",
  "start_by": "string",
  "reason": "string",
  "priority": "string",
  "confidence": float
}
priority rules: Severe/Very Poor -> "high", Poor -> "medium"."""


def category(aqi):
    """Maps a numerical AQI value to its CPCB category."""
    return next(name for hi, name in BANDS if aqi <= hi)


def detect_events(forecast_df, now, min_cat="Poor"):
    """
    Scans the forecast dataframe and detects the first instance 
    where a cell crosses into the danger threshold.
    """
    thr = ORDER.index(min_cat)
    events = []
    
    if forecast_df.empty:
        return events

    # Ensure datetime sorting
    forecast_df = forecast_df.sort_values("datetime")
    
    for cell_id, g in forecast_df.groupby("cell_id"):
        g = g.assign(cat=g["pred_aqi"].apply(category))
        g["rank"] = g["cat"].map(ORDER.index)
        
        bad = g[g["rank"] >= thr]
        if bad.empty:
            continue
            
        first = bad.iloc[0]
        peak = g.loc[g["pred_aqi"].idxmax()]
        lead_time = int((first["datetime"] - now) / pd.Timedelta(hours=1))
        
        events.append({
            "cell_id": str(cell_id),
            "lat": float(first["lat"]),
            "lon": float(first["lon"]),
            "crosses_at": first["datetime"].isoformat(),
            "lead_time_hours": lead_time,
            "category": first["cat"],
            "peak_aqi": int(round(peak["pred_aqi"])),
            "confidence": float(first.get("confidence", 0.7)),
        })
    return events


def generate_fallback_recommendations(events):
    """Deterministic fallback system if the API fails or network drops."""
    logging.warning("Using deterministic fallback template for recommendations.")
    fallback_recs = []
    for ev in events:
        cat = ev["category"]
        grap_info = GRAP.get(cat, {"stage": "Unknown", "measures": ["Monitor AQI levels closely."]})
        primary_measure = grap_info["measures"][0]
        
        priority = "high" if cat in ["Severe", "Very Poor"] else "medium"
        
        fallback_recs.append({
            "cell_id": ev["cell_id"],
            "action": primary_measure,
            "grap_stage": grap_info["stage"],
            "start_by": f"Within {ev['lead_time_hours']} hours",
            "reason": f"AQI predicted to cross into {cat} threshold (Peak: {ev['peak_aqi']}).",
            "priority": priority,
            "confidence": ev["confidence"]
        })
    return fallback_recs


def recommend(events):
    """Queries OpenRouter (Gemma Model) to generate structured recommendations."""
    if not events:
        return []
        
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logging.error("OPENROUTER_API_KEY not found in environment variables.")
        return generate_fallback_recommendations(events)

    try:
        # Pointing the client to the OpenRouter base URL endpoint
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        
        payload = json.dumps({"events": events, "grap": GRAP})
        
        # Calling OpenRouter's free Gemma 4 instruction model 
        response = client.chat.completions.create(
            model="google/gemma-4-31b-it:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": payload}
            ]
        )
        
        text = response.choices[0].message.content
        
        # Clean response string to strip any markdown backticks if Gemma adds them
        text = text[text.find("["): text.rfind("]") + 1]
        return json.loads(text)

    except Exception as e:
        logging.error(f"OpenRouter API Error: {e}")
        return generate_fallback_recommendations(events)