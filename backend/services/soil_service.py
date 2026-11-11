"""
Soil Health Card analysis.

Takes the 12 Soil Health Card parameters (any of them may be missing) and an
optional crop name, and returns:
  * a per-parameter rating with an explanation and a next step,
  * an indicative soil health index (0-100),
  * crop-specific notes (pH preference, salt sensitivity).

The score is a transparent weighted average of per-parameter ratings. It is an
INDICATIVE index for comparing fields and seasons, not an official laboratory
standard.
"""

from backend.knowledge.crops import SALT_SENSITIVE_CLASSES, get_crop_profile
from backend.knowledge.soil_reference import (
    CRITICAL_LIMITS, LABELS, LMH_LIMITS, PARAMETER_INFO, UNITS, WEIGHTS,
)

ALL_PARAMETERS = ["N", "P", "K", "S", "Zn", "Fe", "Cu", "Mn", "B", "pH", "EC", "OC"]

# Points awarded per rating (1.0 = ideal).
POINTS = {"good": 1.0, "medium": 0.75, "high_ok": 0.9, "attention": 0.6, "low": 0.35, "problem": 0.25}


def _fmt(v):
    return f"{v:g}"


def _rate_lmh(param, value):
    low, high = LMH_LIMITS[param]
    unit = UNITS[param]
    reference = f"Low < {_fmt(low)}, Medium {_fmt(low)}–{_fmt(high)}, High > {_fmt(high)} {unit}".strip()
    info = PARAMETER_INFO[param]
    if value < low:
        return dict(status="low", status_label="Low", severity="problem", points=POINTS["low"],
                    reference=reference, next_step=info["low"])
    if value <= high:
        if param == "OC":
            return dict(status="medium", status_label="Medium", severity="ok", points=POINTS["good"],
                        reference=reference,
                        next_step="Organic carbon is moderate. Keep adding manure or compost and crop residues to improve it.")
        return dict(status="medium", status_label="Medium", severity="attention", points=POINTS["medium"],
                    reference=reference,
                    next_step="Level is moderate. Follow the normal recommended nutrient dose for your crop.")
    return dict(status="high", status_label="High", severity="ok",
                points=POINTS["good"] if param == "OC" else POINTS["high_ok"],
                reference=reference, next_step=info["high"])


def _rate_critical(param, value):
    limit = CRITICAL_LIMITS[param]
    reference = f"Deficient below {_fmt(limit)} {UNITS[param]} (critical limit)"
    if value < limit:
        return dict(status="deficient", status_label="Deficient", severity="problem",
                    points=POINTS["low"], reference=reference, next_step=PARAMETER_INFO[param]["low"])
    return dict(status="sufficient", status_label="Sufficient", severity="ok",
                points=POINTS["good"], reference=reference, next_step="No action needed.")


def _rate_ph(value, profile):
    info = PARAMETER_INFO["pH"]
    if value < 5.5:
        status, label = "strongly_acidic", "Strongly acidic"
    elif value < 6.5:
        status, label = "moderately_acidic", "Moderately acidic"
    elif value <= 7.5:
        status, label = "neutral", "Neutral"
    elif value <= 8.5:
        status, label = "moderately_alkaline", "Moderately alkaline"
    else:
        status, label = "strongly_alkaline", "Strongly alkaline"

    reference = "Acidic < 6.5, Neutral 6.5–7.5, Alkaline > 7.5"
    if profile:
        lo, hi = profile["ph"]
        reference += f"; preferred for {profile['name']}: {lo}–{hi}"
        if lo <= value <= hi:
            return dict(status=status, status_label=label, severity="ok", points=POINTS["good"],
                        reference=reference, next_step=f"pH is within the preferred range for {profile['name']}.")
        far = value < lo - 1.0 or value > hi + 1.0
    else:
        if status == "neutral":
            return dict(status=status, status_label=label, severity="ok", points=POINTS["good"],
                        reference=reference, next_step="pH is suitable for most crops.")
        far = status.startswith("strongly")

    step = info["acidic"] if value < 7 else info["alkaline"]
    return dict(status=status, status_label=label, severity="problem" if far else "attention",
                points=POINTS["problem"] if far else POINTS["attention"], reference=reference, next_step=step)


def _rate_ec(value, profile):
    reference = "Normal < 1.0, Caution 1.0–3.0, High > 3.0 dS/m"
    sensitive = bool(profile and profile["salt"] in SALT_SENSITIVE_CLASSES)
    if value < 1.0:
        return dict(status="normal", status_label="Normal", severity="ok", points=POINTS["good"],
                    reference=reference, next_step="Salt level is safe.")
    if value <= 3.0:
        step = ("Salt level may affect seed germination of sensitive crops. "
                "Ensure good drainage and use good-quality irrigation water.")
        if sensitive:
            step = f"{profile['name']} is {profile['salt']} to salt. " + step
        return dict(status="caution", status_label="Caution", severity="problem" if sensitive else "attention",
                    points=POINTS["low"] if sensitive else POINTS["attention"], reference=reference, next_step=step)
    return dict(status="high", status_label="High (saline)", severity="problem", points=POINTS["problem"],
                reference=reference, next_step=PARAMETER_INFO["EC"]["high"])


def analyze_soil(data, crop_name=None):
    """Analyze Soil Health Card values.

    ``data`` is a dict with any subset of ALL_PARAMETERS (None = not provided).
    """
    _, profile = get_crop_profile(crop_name)

    parameters = []
    total_points = 0.0
    total_weight = 0.0
    missing = []

    for p in ALL_PARAMETERS:
        value = data.get(p)
        if value is None:
            missing.append(p)
            continue

        if p in LMH_LIMITS:
            rating = _rate_lmh(p, value)
        elif p in CRITICAL_LIMITS:
            rating = _rate_critical(p, value)
        elif p == "pH":
            rating = _rate_ph(value, profile)
        else:
            rating = _rate_ec(value, profile)

        total_points += rating["points"] * WEIGHTS[p]
        total_weight += WEIGHTS[p]
        parameters.append({
            "parameter": p,
            "label": LABELS[p],
            "value": value,
            "unit": UNITS[p],
            "why_it_matters": PARAMETER_INFO[p]["why"],
            **{k: v for k, v in rating.items() if k != "points"},
        })

    if not parameters:
        return {
            "available": False,
            "soil_score": None,
            "rating": None,
            "message": "No Soil Health Card values were entered, so soil-based analysis is not available. "
                       "You can get a free Soil Health Card from your nearest soil testing laboratory or agriculture office.",
            "parameters": [],
            "problems": [],
            "attention": [],
            "missing": missing,
        }

    score = round(100 * total_points / total_weight)
    if score >= 75:
        rating_label = "Good"
    elif score >= 50:
        rating_label = "Fair"
    else:
        rating_label = "Poor"

    problems = [f"{x['label']}: {x['status_label']}" for x in parameters if x["severity"] == "problem"]
    attention = [f"{x['label']}: {x['status_label']}" for x in parameters if x["severity"] == "attention"]

    crop_notes = []
    if profile:
        lo, hi = profile["ph"]
        crop_notes.append(f"{profile['name']} grows best at soil pH {lo}–{hi}.")
        crop_notes.append(f"{profile['name']} is {profile['salt']} to soil salinity.")
    elif crop_name:
        crop_notes.append(f"No crop-specific reference is stored for '{crop_name}'. General ratings were used.")

    completeness_note = None
    if missing:
        completeness_note = (f"{len(missing)} of 12 values were not entered "
                             f"({', '.join(missing)}). The score is based only on the values provided.")

    return {
        "available": True,
        "soil_score": score,
        "rating": rating_label,
        "crop": profile["name"] if profile else crop_name,
        "parameters_provided": len(parameters),
        "missing": missing,
        "completeness_note": completeness_note,
        "parameters": parameters,
        "problems": problems,
        "attention": attention,
        "crop_notes": crop_notes,
        "disclaimer": "Indicative soil health index based on standard Soil Health Card rating limits. "
                      "Fertilizer doses must follow the recommendation printed on your Soil Health Card "
                      "or advice from your KVK / agriculture officer.",
    }
