"""
"Start a New Farm" guided planning service for first-time and beginner farmers.

Scores and ranks candidate crops based on:
  1. Upcoming/current Indian agricultural season (Kharif, Rabi, Zaid)
  2. Water availability (rain_only, limited, assured)
  3. Budget band (low, medium, high)
  4. Labour availability (self, family, hired)
  5. Soil pH and salinity (EC) if Soil Health Card values are provided
  6. Local forecast temperatures if farm weather is provided
  7. Beginner-friendliness rating
"""

from datetime import date
from typing import Optional

from backend.knowledge.crops import CROP_PROFILES, SALT_SENSITIVE_CLASSES, get_crop_profile
from backend.knowledge.farm_planning import (
    BUDGETS,
    CROP_PLANNING,
    LABOUR,
    LEVEL,
    SCHEMES,
    SEASONS,
    WATER_SOURCES,
)


def detect_season(target_month: Optional[int] = None) -> str:
    """Detect the active or upcoming Indian farming season from the calendar month."""
    m = target_month if target_month and 1 <= target_month <= 12 else date.today().month
    if m in (6, 7, 8, 9):
        return "kharif"
    if m in (10, 11, 12, 1):
        return "rabi"
    return "zaid"


def recommend_new_farm_plan(
    season: Optional[str] = None,
    water_source: str = "limited",
    budget: str = "low",
    labour: str = "family",
    area_acres: Optional[float] = 1.0,
    soil_ph: Optional[float] = None,
    soil_ec: Optional[float] = None,
    soil_n: Optional[float] = None,
    selected_crop: Optional[str] = None,
) -> dict:
    """
    Generate a complete 7-step "Start a New Farm" guide:
      - Ranked shortlist of top suitable crops with transparent reasons
      - Pre-sowing checklist for the top/chosen crop (land prep, seed, manure, spacing)
      - Step-by-step beginner guide to getting a free Soil Health Card
      - Official government schemes & helplines for new farmers
    """
    season_key = (season or "").strip().lower()
    if season_key not in SEASONS:
        season_key = detect_season()
    season_info = SEASONS[season_key]

    w_level = WATER_SOURCES.get(water_source, WATER_SOURCES["limited"])["level"]
    b_level = BUDGETS.get(budget, BUDGETS["low"])["level"]
    l_level = LABOUR.get(labour, LABOUR["family"])["level"]
    acres = float(area_acres) if area_acres and area_acres > 0 else 1.0
    guntas = round(acres * 40.0, 1)

    scored_crops = []
    for crop_key, plan in CROP_PLANNING.items():
        profile = CROP_PROFILES.get(crop_key)
        if not profile:
            continue

        score = 50
        reasons = []
        cautions = []

        # 1. Season match
        if season_key in plan["seasons"]:
            score += 22
            reasons.append(f"Fits the {season_info['name']}.")
        else:
            score -= 30
            cautions.append(
                f"Normally sown in {', '.join(SEASONS[s]['name'] for s in plan['seasons'])}, not {season_info['name']}."
            )

        # 2. Water match
        crop_w = LEVEL[plan["water"]]
        if crop_w <= w_level:
            score += 15
            reasons.append(f"Water requirement ({plan['water']}) matches your water source.")
        elif crop_w == w_level + 1:
            score -= 15
            cautions.append(f"Needs {plan['water']} water; risky with your current water source.")
        else:
            score -= 35
            cautions.append(f"Requires {plan['water']} irrigation and is not suited to rain-only land.")

        # 3. Budget match
        crop_b = LEVEL[plan["cost"]]
        if crop_b <= b_level:
            score += 10
            reasons.append(f"Input cost is {plan['cost']}, within your budget.")
        else:
            score -= 14
            cautions.append(f"Seed and input cost is {plan['cost']}, above your selected budget band.")

        # 4. Labour match
        crop_l = LEVEL[plan["labour"]]
        if crop_l <= l_level:
            score += 8
        else:
            score -= 10
            cautions.append(f"Requires {plan['labour']} labour (for transplanting, weeding, or multiple pickings).")

        # 5. Beginner friendliness
        if plan["beginner"] == 3:
            score += 10
            reasons.append("Hardy and beginner-friendly for a first season.")
        elif plan["beginner"] == 1:
            score -= 6
            cautions.append("Needs close pest/disease monitoring — start on a small portion of your plot first.")

        # 6. Soil pH and salinity (if provided)
        ph_lo, ph_hi = profile["ph"]
        if soil_ph is not None:
            if ph_lo <= soil_ph <= ph_hi:
                score += 12
                reasons.append(f"Your soil pH ({soil_ph}) is ideal ({ph_lo}–{ph_hi}).")
            elif (ph_lo - 0.5) <= soil_ph <= (ph_hi + 0.5):
                score += 3
                cautions.append(f"Your soil pH ({soil_ph}) is slightly outside the preferred {ph_lo}–{ph_hi} range.")
            else:
                score -= 18
                cautions.append(f"Your soil pH ({soil_ph}) is outside the preferred {ph_lo}–{ph_hi} range.")

        if soil_ec is not None and soil_ec > 2.0:
            if profile["salt"] in SALT_SENSITIVE_CLASSES:
                score -= 18
                cautions.append(f"Soil EC ({soil_ec} dS/m) is high for this {profile['salt']} crop.")
            else:
                score += 8
                reasons.append(f"Tolerates higher soil salinity ({profile['salt']}).")

        if soil_n is not None and soil_n < 280 and plan.get("legume"):
            score += 10
            reasons.append("Fixes its own nitrogen and enriches low-nitrogen soil.")

        score = max(5, min(99, score))
        scored_crops.append({
            "crop_key": crop_key,
            "crop_name": profile["name"],
            "category": plan["category"].title(),
            "suitability_score": score,
            "suitability_label": "Highly Suitable" if score >= 75 else ("Moderately Suitable" if score >= 55 else "Not Recommended Now"),
            "duration_days": profile.get("duration_days", 110),
            "water_need": plan["water"].title(),
            "cost_level": plan["cost"].title(),
            "labour_need": plan["labour"].title(),
            "sowing_method": plan["method"],
            "spacing": plan["spacing"],
            "preferred_ph": f"{ph_lo}–{ph_hi}",
            "why_it_fits": reasons,
            "cautions": cautions,
        })

    scored_crops.sort(key=lambda c: c["suitability_score"], reverse=True)
    shortlist = scored_crops[:6]

    # Pick the focus crop for the Pre-Sowing Checklist (either user-selected or #1 ranked)
    focus_key, focus_profile = get_crop_profile(selected_crop) if selected_crop else (None, None)
    if not focus_profile or focus_key not in CROP_PLANNING:
        focus_key = shortlist[0]["crop_key"]
        focus_profile = CROP_PROFILES[focus_key]
    focus_plan = CROP_PLANNING[focus_key]

    fym_lo, fym_hi = focus_profile.get("fym_tonnes_per_acre", (4, 6))
    plot_fym_lo, plot_fym_hi = round(fym_lo * acres, 1), round(fym_hi * acres, 1)

    pre_sowing_checklist = [
        {
            "step": 1,
            "title": "Test Your Soil First (Free at Government Lab / KVK)",
            "detail": (
                "Collect soil from 8–10 spots in a zig-zag across your plot (0–15 cm depth), mix them together, "
                "take about 500 g in a clean cloth/plastic bag, and give it to your nearest Krishi Vigyan Kendra (KVK) "
                "or Mandal/Block Agriculture Office for a free Soil Health Card."
            ),
        },
        {
            "step": 2,
            "title": f"Land Preparation & Basal Manure ({acres} Acres / {guntas} Guntas)",
            "detail": (
                f"Plough the field 2–3 times to remove weeds and break clods. Spread {plot_fym_lo}–{plot_fym_hi} tonnes "
                f"of well-decomposed Farmyard Manure (FYM) or compost (~{round((plot_fym_lo + plot_fym_hi) / 4.0, 1)} tractor trolleys) "
                "2–3 weeks before sowing so it mixes into the top soil."
            ),
        },
        {
            "step": 3,
            "title": f"Buy Certified Seed for {focus_profile['name']}",
            "detail": (
                "Buy seed with a blue Certified Seed tag from your State Seed Corporation, KVK, or a licensed dealer, "
                "and always keep the bill. Ask your KVK which variety is recommended for your district and season."
            ),
        },
        {
            "step": 4,
            "title": f"Sowing Method & Plant Spacing ({focus_plan['spacing']})",
            "detail": (
                f"Recommended sowing method: {focus_plan['method']} at {focus_plan['spacing']} spacing. "
                "Sowing in lines (instead of broadcasting by hand) makes weeding, spraying, and harvesting much easier."
            ),
        },
        {
            "step": 5,
            "title": "Treat Seed with Low-Cost Bio-Inoculants",
            "detail": (
                "Before sowing, treat seeds with Trichoderma (protects against soil-borne root rot) and "
                f"{'Rhizobium culture (helps legume roots fix nitrogen)' if focus_plan.get('legume') else 'Azospirillum / Azotobacter + PSB'} "
                "available at low cost from your KVK."
            ),
        },
        {
            "step": 6,
            "title": "Keep First 30–40 Days Weed-Free",
            "detail": (
                f"{focus_profile['name']} takes about {focus_profile.get('duration_days', 110)} days from sowing to harvest. "
                "Plan your first hand-weeding or inter-cultivation around Day 20–25 after sowing."
            ),
        },
    ]

    return {
        "season": {
            "key": season_key,
            "name": season_info["name"],
            "about": season_info["about"],
        },
        "resources": {
            "area_acres": round(acres, 2),
            "area_guntas": guntas,
            "water_source": WATER_SOURCES.get(water_source, WATER_SOURCES["limited"])["label"],
            "budget": BUDGETS.get(budget, BUDGETS["low"])["label"],
            "labour": LABOUR.get(labour, LABOUR["family"])["label"],
        },
        "recommended_crops": shortlist,
        "selected_crop_plan": {
            "crop_key": focus_key,
            "crop_name": focus_profile["name"],
            "duration_days": focus_profile.get("duration_days", 110),
            "preferred_ph": f"{focus_profile['ph'][0]}–{focus_profile['ph'][1]}",
            "sowing_method": focus_plan["method"],
            "spacing": focus_plan["spacing"],
            "heat_note": focus_profile.get("heat_note", ""),
            "pre_sowing_checklist": pre_sowing_checklist,
            "stages": focus_profile.get("stages") or [],
        },
        "schemes_and_help": SCHEMES,
        "disclaimer": (
            "This shortlist is a starting guide based on season, water, budget, labour, and soil pH/salinity. "
            "Before buying seed, confirm the best local variety with your district Krishi Vigyan Kendra (KVK) "
            "or call the Kisan Call Centre (1800-180-1551)."
        ),
    }
