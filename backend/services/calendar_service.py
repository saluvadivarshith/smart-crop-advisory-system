"""
Crop Stage Calendar, Plot-Scaled Water & Organic Matter Calculator,
and Smart Soil Health Card Text Parser.
"""

from datetime import date, datetime, timedelta
import re
from typing import Optional

from backend.knowledge.crops import CROP_PROFILES, get_crop_profile

SQ_METERS_PER_ACRE = 4046.8564224

DEFAULT_STAGE_TIMELINE = [
    {"stage": "seedling", "days": (0, 22), "title": "Seedling & Establishment (Days 0–22)", "tasks": "Ensure healthy stand establishment, good drainage, and early weed control."},
    {"stage": "vegetative", "days": (23, 50), "title": "Active Vegetative Growth (Days 23–50)", "tasks": "Keep rows weed-free, monitor lower leaves for early spots, and maintain balanced soil moisture."},
    {"stage": "flowering", "days": (51, 75), "title": "Flowering & Pollination (Days 51–75)", "tasks": "Critical moisture stage — avoid drought or waterlogging during flowering."},
    {"stage": "fruiting", "days": (76, 100), "title": "Fruit / Pod / Grain Filling (Days 76–100)", "tasks": "Protect upper canopy health and remove diseased plant parts promptly."},
    {"stage": "maturity", "days": (101, 120), "title": "Maturity & Harvest (Days 101+)", "tasks": "Harvest in dry weather at proper maturity and remove infected crop residue."},
]


def get_crop_calendar(
    crop_name: str,
    sowing_date_str: Optional[str] = None,
    current_stage: Optional[str] = None,
    area_acres: Optional[float] = None,
    weather_result: Optional[dict] = None,
) -> dict:
    """Build a stage-by-stage crop calendar and plot-scaled field calculations."""
    _, profile = get_crop_profile(crop_name)
    display_crop = profile["name"] if profile else (crop_name or "Tomato")
    stages_def = (profile.get("stages") if profile and profile.get("stages") else DEFAULT_STAGE_TIMELINE)
    duration_days = profile.get("duration_days", 115) if profile else 115

    today = date.today()
    sowing_dt: Optional[date] = None
    days_after_sowing: Optional[int] = None

    if sowing_date_str:
        try:
            sowing_dt = datetime.strptime(sowing_date_str[:10], "%Y-%m-%d").date()
            days_after_sowing = max(0, (today - sowing_dt).days)
        except ValueError:
            sowing_dt = None

    timeline = []
    detected_stage = current_stage or "vegetative"

    for idx, st in enumerate(stages_def):
        d_start, d_end = st["days"]
        start_date_str = (sowing_dt + timedelta(days=d_start)).isoformat() if sowing_dt else None
        end_date_str = (sowing_dt + timedelta(days=d_end)).isoformat() if sowing_dt else None

        if days_after_sowing is not None:
            if days_after_sowing > d_end and idx < len(stages_def) - 1:
                status = "completed"
            elif d_start <= days_after_sowing <= d_end or (idx == len(stages_def) - 1 and days_after_sowing >= d_start):
                status = "current"
                detected_stage = st["stage"]
            else:
                status = "upcoming"
        else:
            status = "current" if st["stage"] == detected_stage else "upcoming"

        timeline.append({
            "step": idx + 1,
            "stage": st["stage"],
            "title": st["title"],
            "day_range": f"Day {d_start}–{d_end}",
            "start_date": start_date_str,
            "end_date": end_date_str,
            "status": status,
            "tasks": st["tasks"],
        })

    expected_harvest = (sowing_dt + timedelta(days=duration_days)).isoformat() if sowing_dt else None

    # Plot-scaled water & organic matter estimates
    acres = float(area_acres) if area_acres and area_acres > 0 else 1.0
    guntas = round(acres * 40.0, 1)
    sq_meters = round(acres * SQ_METERS_PER_ACRE)

    fym_lo, fym_hi = profile.get("fym_tonnes_per_acre", (5, 8)) if profile else (5, 8)
    plot_fym_tonnes = (round(fym_lo * acres, 1), round(fym_hi * acres, 1))

    water_balance_plot = None
    if weather_result and weather_result.get("irrigation"):
        irr = weather_result["irrigation"]
        rain_mm = float(irr.get("rain_next_3_days_mm") or 0.0)
        et0_mm = float(irr.get("et0_next_3_days_mm") or 0.0)
        deficit_mm = float(irr.get("water_deficit_mm") or 0.0)
        # 1 mm of water over 1 m² = 1 Liter
        water_balance_plot = {
            "rain_liters": round(rain_mm * sq_meters),
            "et0_loss_liters": round(et0_mm * sq_meters),
            "net_deficit_liters": round(deficit_mm * sq_meters),
            "rain_mm": rain_mm,
            "et0_mm": et0_mm,
            "deficit_mm": deficit_mm,
            "advice": irr.get("advice"),
        }

    return {
        "crop": display_crop,
        "sowing_date": sowing_dt.isoformat() if sowing_dt else None,
        "days_after_sowing": days_after_sowing,
        "detected_stage": detected_stage,
        "duration_days": duration_days,
        "expected_harvest_date": expected_harvest,
        "plot_area": {
            "acres": round(acres, 2),
            "guntas": guntas,
            "sq_meters": sq_meters,
            "is_custom_area": bool(area_acres and area_acres > 0),
        },
        "organic_manure_guide": {
            "fym_tonnes_min": plot_fym_tonnes[0],
            "fym_tonnes_max": plot_fym_tonnes[1],
            "tractor_trolleys_approx": round(sum(plot_fym_tonnes) / 2.0 / 2.0, 1),  # ~2 tonnes per trolley
            "note": (
                f"For {round(acres, 2)} acre ({guntas} guntas) of {display_crop}, general pre-sowing "
                f"Farmyard Manure / Compost guidance is {plot_fym_tonnes[0]}–{plot_fym_tonnes[1]} tonnes "
                f"applied 2–3 weeks before sowing/planting."
            ),
        },
        "water_balance_plot": water_balance_plot,
        "timeline": timeline,
    }


# Regex patterns to extract values from pasted Soil Health Card text
SOIL_REGEX_PATTERNS = {
    "N": r"(?:available\s+)?(?:nitrogen(?:\s*\(n\))?|(?<![a-z])n(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "P": r"(?:available\s+)?(?:phosphorus(?:\s*\(p(?:2o5)?\))?|p2o5|(?<![a-z])p(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "K": r"(?:available\s+)?(?:potassium(?:\s*\(k(?:2o)?\))?|k2o|(?<![a-z])k(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "OC": r"(?:organic\s+carbon(?:\s*\(oc\))?|(?<![a-z])oc(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "pH": r"(?:soil\s+)?ph\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "EC": r"(?:electrical\s+conductivity(?:\s*\(ec\))?|(?<![a-z])ec(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "S": r"(?:available\s+)?(?:sulphur(?:\s*\(s\))?|sulfur(?:\s*\(s\))?|(?<![a-z])s(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "Zn": r"(?:available\s+)?(?:zinc(?:\s*\(zn\))?|(?<![a-z])zn(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "Fe": r"(?:available\s+)?(?:iron(?:\s*\(fe\))?|(?<![a-z])fe(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "Cu": r"(?:available\s+)?(?:copper(?:\s*\(cu\))?|(?<![a-z])cu(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "Mn": r"(?:available\s+)?(?:manganese(?:\s*\(mn\))?|(?<![a-z])mn(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    "B": r"(?:available\s+)?(?:boron(?:\s*\(b\))?|(?<![a-z])b(?![a-z]))\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
}


def parse_soil_card_text(raw_text: str) -> dict:
    """Extract Soil Health Card numerical values from pasted report text."""
    text = (raw_text or "").strip()
    extracted = {}
    for param, pattern in SOIL_REGEX_PATTERNS.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                extracted[param] = float(match.group(1))
            except ValueError:
                pass
    return {
        "extracted_count": len(extracted),
        "values": extracted,
    }
