"""
grap.py — Task #43
Maps forecasted AQI values to the official Graded Response Action Plan (GRAP)
stages and returns the real, official measures for that stage.

SOURCE OF TRUTH:
GRAP is issued by the Commission for Air Quality Management in NCR and
Adjoining Areas (CAQM) under the CAQM Act, 2021, following the Supreme
Court's directions in M.C. Mehta v. Union of India. Current schedule:
"Graded Response Action Plan (GRAP) for the National Capital Region (NCR)",
Revision dated 21.11.2025 — https://caqm.nic.in

PROJECT FRAMING (read before demo/Q&A):
This module implements "GRAP-Ahmedabad" — a proposed extension of CAQM's
NCR staged-response framework to Ahmedabad's 1km forecast grid. It is a
forward-looking civic-tech proposal, not a claim that AMC/GPCB has
adopted GRAP today. The four AQI-category thresholds used below (Poor/
Very Poor/Severe/Severe+) ARE the same national CPCB AQI categories used
pan-India, and the stage actions are the real, currently-notified CAQM
measures — nothing here is invented. What's proposed is applying that
same staged-response *logic* to a city that doesn't yet have one,
grid-cell by grid-cell instead of city-wide. Frame it to judges as
"GRAP-Ahmedabad: a proposed GRAP-style staged response for Ahmedabad,
built on real CAQM thresholds and measures (Rev. 21.11.2025)."

Each action string below is a faithful paraphrase (not a verbatim
reproduction) of an actual numbered action in the official CAQM schedule,
tagged with its clause number so it can be traced back to the source PDF.
"""

from dataclasses import dataclass, field
from typing import Optional

GRAP_SOURCE = {
    "issuing_authority": "Commission for Air Quality Management in NCR and Adjoining Areas (CAQM)",
    "document": "Graded Response Action Plan (GRAP) for the National Capital Region (NCR)",
    "revision": "21.11.2025",
    "url": "https://caqm.nic.in",
    "applies_to": "National Capital Region (NCR) — legally binding there today",
    "this_project": (
        "GRAP-Ahmedabad: a proposed extension applying CAQM's real thresholds "
        "and measures to Ahmedabad's 1km grid. Not a claim of current legal "
        "adoption by AMC/GPCB."
    ),
}


@dataclass
class GrapStage:
    stage_id: int
    stage_name: str          # e.g. "Stage I"
    category: str            # e.g. "Poor"
    aqi_min: int
    aqi_max: Optional[int]   # None => open-ended (Stage IV)
    color: str
    severity_rank: int       # 0-4, 0 = below GRAP scope
    key_actions: list = field(default_factory=list)
    citizen_advisory: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# The four GRAP stages, thresholds exactly as notified by CAQM (Rev. 21.11.2025)
# ---------------------------------------------------------------------------
GRAP_STAGES = [
    GrapStage(
        stage_id=1,
        stage_name="Stage I",
        category="Poor",
        aqi_min=201,
        aqi_max=300,
        color="#F4A93B",
        severity_rank=1,
        key_actions=[
            "[Cl.1-2] Enforce dust-mitigation rules at Construction & Demolition (C&D) sites; block unregistered/non-compliant C&D projects ≥500 sqm from operating.",
            "[Cl.4] Run mechanized road sweeping and water sprinkling on identified roads; ensure dust collected is disposed of at designated sites.",
            "[Cl.8-9] Strictly prohibit open burning of biomass and municipal solid waste, including at landfill/dump sites.",
            "[Cl.10-14] Deploy traffic police at congestion-prone corridors; strictly enforce Pollution Under Control (PUC) norms and act on visibly polluting vehicles.",
            "[Cl.15-18] Take penal action against non-compliant industries, brick kilns, hot-mix plants and thermal plants violating emission norms.",
            "[Cl.25-26] Push public advisories via SMS/social media/apps and route citizen pollution complaints to a control room for quick redressal.",
            "[Cl.31] Increase frequency of CNG/electric public transport (buses/metro) and consider off-peak fare incentives.",
        ],
        citizen_advisory=[
            "Keep vehicles properly tuned and PUC-certified; do not idle at signals.",
            "Avoid burning waste/biomass in the open.",
            "Report polluting activity via municipal apps.",
        ],
    ),
    GrapStage(
        stage_id=2,
        stage_name="Stage II",
        category="Very Poor",
        aqi_min=301,
        aqi_max=400,
        color="#E4572E",
        severity_rank=2,
        key_actions=[
            "[Cl.1-2] Intensify mechanized sweeping/water sprinkling — more shifts/hours, prioritizing traffic hotspots and heavy-corridor roads.",
            "[Cl.4] Launch focused, sector-specific remediation in every identified pollution hotspot in the city.",
            "[Cl.5] Enforce the graded diesel-generator (DG set) restriction schedule (capacity-based), permitting DG use only for defined emergency services where gas/retrofit alternatives are unavailable.",
            "[Cl.6] Raise parking fees in congested zones to discourage private-vehicle trips.",
            "[Cl.9] Consider staggered office/school timings across public and municipal bodies to spread out peak-hour traffic load.",
        ],
        citizen_advisory=[
            "Prefer public transport; combine/reduce non-essential trips.",
            "Replace vehicle air filters at recommended intervals.",
            "Avoid dust-heavy construction/renovation work at home.",
        ],
    ),
    GrapStage(
        stage_id=3,
        stage_name="Stage III",
        category="Severe",
        aqi_min=401,
        aqi_max=450,
        color="#A62E2E",
        severity_rank=3,
        key_actions=[
            "[Cl.1] Halt high-dust C&D activity citywide (excavation, piling, demolition, road works, RMC batching) except for essential/linear public infra, hospitals and national-security projects.",
            "[Cl.2-3] Shut down stone crushers and mining/associated operations in and around the city.",
            "[Cl.4-6] Restrict plying of BS-III petrol / BS-IV diesel light vehicles and older diesel goods vehicles within city limits, barring essential-goods carriers.",
            "[Cl.7] Move classes up to Class V to hybrid (physical + online) mode.",
            "[Cl.8-9] Evaluate 50% work-from-home for public/private offices to cut commute-linked emissions.",
        ],
        citizen_advisory=[
            "Prefer walking/cycling for short trips; work from home if possible.",
            "Avoid coal/wood for heating or cooking outdoors.",
            "Sensitive groups (children, elderly, respiratory/cardiac patients) minimize outdoor exposure.",
        ],
    ),
    GrapStage(
        stage_id=4,
        stage_name="Stage IV",
        category="Severe+",
        aqi_min=451,
        aqi_max=None,
        color="#6A0DAD",
        severity_rank=4,
        key_actions=[
            "[Cl.1-2] Stop non-essential truck/HGV entry into the city; allow only LNG/CNG/Electric/BS-VI diesel and essential-goods vehicles.",
            "[Cl.3] Extend the Stage III C&D ban to linear public projects (roads, flyovers, power/telecom lines) as well.",
            "[Cl.4] Extend hybrid schooling to classes VI–IX and XI.",
            "[Cl.5] Evaluate emergency measures: closure of colleges/non-essential commercial activity, and odd-even vehicle rationing by registration number.",
        ],
        citizen_advisory=[
            "Children, elderly and those with chronic respiratory/cardiac/cerebrovascular conditions should stay indoors; wear a mask if going out is unavoidable.",
        ],
    ),
]

# AQI below 201 is outside GRAP's scope (Good/Satisfactory/Moderate on the
# national CPCB scale) — no CAQM stage action is triggered, but we still
# want a "no action needed" placeholder so downstream code never null-checks.
NO_STAGE = GrapStage(
    stage_id=0,
    stage_name="No Stage",
    category="Satisfactory / Moderate",
    aqi_min=0,
    aqi_max=200,
    color="#6FCB6F",
    severity_rank=0,
    key_actions=["No GRAP-level action required. Routine monitoring only."],
    citizen_advisory=["Air quality is within acceptable limits."],
)

DANGEROUS_AQI_THRESHOLD = 201  # first AQI value at which GRAP engages


def get_grap_stage(aqi: float) -> GrapStage:
    """Return the GrapStage object an AQI value falls into."""
    if aqi is None:
        return NO_STAGE
    aqi = float(aqi)
    if aqi < 201:
        return NO_STAGE
    for stage in GRAP_STAGES:
        if stage.aqi_max is None:
            if aqi >= stage.aqi_min:
                return stage
        elif stage.aqi_min <= aqi <= stage.aqi_max:
            return stage
    return NO_STAGE  # aqi < 0 or malformed, defensive fallback


def stage_to_dict(stage: GrapStage) -> dict:
    return {
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "category": stage.category,
        "aqi_range": [stage.aqi_min, stage.aqi_max],
        "color": stage.color,
        "severity_rank": stage.severity_rank,
        "key_actions": stage.key_actions,
        "citizen_advisory": stage.citizen_advisory,
        "source": GRAP_SOURCE,
    }


def get_recommendation(aqi: float, max_actions: int = 4) -> dict:
    """
    Convenience wrapper used by advisor.py: given a predicted AQI value,
    return the stage info trimmed to the top N most actionable measures
    (highest-clause-priority first, as ordered in GRAP_STAGES).
    """
    stage = get_grap_stage(aqi)
    d = stage_to_dict(stage)
    d["key_actions"] = d["key_actions"][:max_actions]
    return d


if __name__ == "__main__":
    for test_aqi in [150, 250, 340, 420, 480]:
        s = get_grap_stage(test_aqi)
        print(f"AQI {test_aqi:>4} -> {s.stage_name} ({s.category})")