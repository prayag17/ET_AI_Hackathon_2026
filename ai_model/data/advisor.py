import os
import json
import logging
import pandas as pd
from openai import OpenAI  # OpenRouter uses the OpenAI library structure

try:
    from grap import GRAP_STAGES, get_recommendation
except ModuleNotFoundError:
    from ai_model.grap import GRAP_STAGES, get_recommendation

# Configure logging to monitor fallback triggers
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Hardcoded constants for GRAP mapping
ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe", "Severe+"]
BANDS = [
    (50, "Good"), (100, "Satisfactory"), (200, "Moderate"),
    (300, "Poor"), (400, "Very Poor"), (10000, "Severe"), (10000, "Severe+")
]

GRAP = {
    stage.category:{
        "stage": stage.stage_name,
        "measures": stage.key_actions[:3],
    }
    for stage in GRAP_STAGES
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
        rec = get_recommendation(ev["peak_aqi"], max_actions=1)
        primary_measure = rec["key_actions"][0] if rec["key_actions"] else "Monitor AQI levels closely."
        priority = "high" if rec["severity_rank"] >= 2 else "medium"
        
        fallback_recs.append({
            "cell_id": ev["cell_id"],
            "action": primary_measure,
            "grap_stage": rec["stage_name"],
            "start_by": f"Within {ev['lead_time_hours']} hours",
            "reason": f"AQI predicted to cross into {ev['category']} threshold (Peak: {ev['peak_aqi']}).",
            "priority": priority,
            "confidence": ev["confidence"],
            "grap_source": rec["source"],
            "stage_color": rec["color"],
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
        recs = json.loads(text)
        
        stage_source = {s.stage_name: s for s in GRAP_STAGES}
        for r in recs:
            s = stage_source.get(r.get("grap_stage"))
            if s:
                r["grap_source"] = get_recommendation(s.aqi_min, max_actions=1)["source"]
                r["stage_color"] = s.color
        return recs

    except Exception as e:
        logging.error(f"OpenRouter API Error: {e}")
        return generate_fallback_recommendations(events)