"""
"What to Buy" input guide: fertilizer quantities, organic and bio-inputs,
plant protection (IPM sequence) and weed management, combined into a
shopping list for the farmer's exact plot size.

See backend/knowledge/farm_inputs.py for the design rules and sources.
In short: fertilizer quantities are calculated transparently from a nutrient
dose; chemical pesticides and herbicides are never named or dosed.
"""

import math
from typing import Optional

from backend.knowledge.crops import get_crop_profile
from backend.knowledge.diseases import DISEASE_BY_KEY, find_disease
from backend.knowledge.farm_inputs import (
    BIO_OPTIONS,
    BIOFERTILIZERS,
    CROP_PESTS,
    DISEASE_TYPE_TO_BIO,
    FERTILIZERS,
    GENERAL_RDF,
    LEGUMES,
    MONITORING_TOOLS,
    OILSEEDS,
    PESTICIDE_SAFETY,
    WHERE_TO_BUY,
)
from backend.knowledge.farm_planning import CROP_PLANNING
from backend.knowledge.soil_reference import CRITICAL_LIMITS, LMH_LIMITS

HA_PER_ACRE = 0.404686
ZINC_SULPHATE_KG_PER_HA = 25.0   # common general soil application of zinc sulphate heptahydrate
SOIL_FACTOR = {"low": 1.25, "medium": 1.0, "high": 0.75}


def _rating(param: str, value) -> Optional[str]:
    if value is None or param not in LMH_LIMITS:
        return None
    lo, hi = LMH_LIMITS[param]
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "medium"


def _num(d: Optional[dict], key: str):
    if not d:
        return None
    v = d.get(key)
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _product_line(key: str, kg: float, prices: Optional[dict]) -> dict:
    f = FERTILIZERS[key]
    kg = max(0.0, kg)
    bags_exact = kg / f["bag_kg"]
    line = {
        "product_key": key,
        "product": f["name"],
        "kg": round(kg, 1),
        "bag_kg": f["bag_kg"],
        "bags_exact": round(bags_exact, 2),
        "bags_to_buy": math.ceil(bags_exact - 1e-9) if kg > 0 else 0,
        "price_per_bag": None,
        "estimated_cost": None,
    }
    price = _num(prices, key)
    if price is not None and price > 0:
        line["price_per_bag"] = price
        line["estimated_cost"] = round(bags_exact * price, 0)
    return line


def _stage_start(profile: Optional[dict], stage: str, default: int) -> int:
    for st in (profile or {}).get("stages") or []:
        if st.get("stage") == stage:
            return int(st["days"][0])
    return default


def build_fertilizer_plan(
    crop_key: str,
    profile: Optional[dict],
    area_acres: float,
    soil: Optional[dict] = None,
    shc_npk: Optional[dict] = None,
    prices: Optional[dict] = None,
) -> dict:
    """Calculate fertilizer product quantities for the plot."""
    shc_n, shc_p, shc_k = _num(shc_npk, "N"), _num(shc_npk, "P"), _num(shc_npk, "K")
    notes = []

    if shc_n is not None and shc_p is not None and shc_k is not None:
        base = (shc_n, shc_p, shc_k)
        source = "Soil Health Card recommendation (entered by you)"
        adjust = False
    elif crop_key in GENERAL_RDF:
        base = GENERAL_RDF[crop_key]
        source = "General recommended dose (ICAR / State Agricultural University reference)"
        adjust = True
    else:
        return {
            "available": False,
            "message": (
                f"No general field-crop fertilizer reference is stored for {profile['name'] if profile else crop_key}. "
                "Orchard and specialty crops need per-tree or crop-specific schedules. Please use the fertilizer "
                "recommendation printed on your Soil Health Card or ask your horticulture officer / KVK."
            ),
        }

    n, p, k = base
    adjustments = []
    if adjust:
        if soil and any(_num(soil, x) is not None for x in ("N", "P", "K")):
            for label, param, idx in (("Nitrogen", "N", 0), ("Phosphorus", "P", 1), ("Potassium", "K", 2)):
                rating = _rating(param, _num(soil, param))
                if not rating:
                    continue
                if param == "N" and crop_key in LEGUMES:
                    adjustments.append(f"{label}: soil is {rating}, but pulses and oilseed legumes only need a small starter dose, so it is not changed.")
                    continue
                factor = SOIL_FACTOR[rating]
                if factor != 1.0:
                    adjustments.append(
                        f"{label}: your soil test is {rating.upper()}, so the dose is "
                        f"{'increased' if factor > 1 else 'reduced'} by 25%."
                    )
                else:
                    adjustments.append(f"{label}: your soil test is MEDIUM, so the general dose is used.")
                vals = [n, p, k]
                vals[idx] = vals[idx] * factor
                n, p, k = vals
        else:
            notes.append(
                "No soil test values were given, so the general dose is used. A free Soil Health Card test "
                "often shows you can buy less fertilizer."
            )

    ha = area_acres * HA_PER_ACRE
    need_n, need_p, need_k = n * ha, p * ha, k * ha

    # Option A: Urea + DAP + MOP
    dap_kg = need_p / FERTILIZERS["dap"]["P2O5"]
    n_from_dap = dap_kg * FERTILIZERS["dap"]["N"]
    urea_a = max(0.0, need_n - n_from_dap) / FERTILIZERS["urea"]["N"]
    mop_kg = need_k / FERTILIZERS["mop"]["K2O"]
    option_a = [_product_line("urea", urea_a, prices), _product_line("dap", dap_kg, prices), _product_line("mop", mop_kg, prices)]

    # Option B: Urea + SSP + MOP (SSP also supplies sulphur and calcium)
    ssp_kg = need_p / FERTILIZERS["ssp"]["P2O5"]
    urea_b = need_n / FERTILIZERS["urea"]["N"]
    option_b = [_product_line("urea", urea_b, prices), _product_line("ssp", ssp_kg, prices), _product_line("mop", mop_kg, prices)]
    sulphur_from_ssp = round(ssp_kg * FERTILIZERS["ssp"]["S"], 1)

    s_val = _num(soil, "S")
    s_low = s_val is not None and s_val < CRITICAL_LIMITS["S"]
    prefer_b = s_low or crop_key in LEGUMES or crop_key in OILSEEDS
    if s_low:
        why = "Option B is suggested because your soil is low in sulphur and SSP supplies sulphur along with phosphorus."
    elif prefer_b:
        why = "Option B is suggested because pulses and oilseeds benefit from the sulphur and calcium in SSP."
    else:
        why = "Option A needs fewer bags to carry. Option B (with SSP) is also fine and adds sulphur."

    for opt in (option_a, option_b):
        for line in opt:
            if line["kg"] == 0:
                line["note"] = "Not needed for this crop / soil."

    # Split schedule for nitrogen (P and K go fully at sowing)
    rec_option = option_b if prefer_b else option_a
    urea_total = rec_option[0]["kg"]
    p_product = rec_option[1]
    if crop_key in LEGUMES or need_n <= 0:
        schedule = [{
            "when": "At sowing (basal)",
            "day": 0,
            "items": [f"{line['product']}: {line['kg']} kg" for line in rec_option if line["kg"] > 0],
            "note": "Pulses and oilseed legumes get their whole fertilizer dose at sowing.",
        }]
    else:
        veg_day = _stage_start(profile, "vegetative", 25)
        flow_day = _stage_start(profile, "flowering", 50)
        n_basal_target = need_n * 0.5
        n_from_p = p_product["kg"] * FERTILIZERS[p_product["product_key"]]["N"]
        urea_basal = max(0.0, n_basal_target - n_from_p) / FERTILIZERS["urea"]["N"]
        urea_rest = max(0.0, urea_total - urea_basal)
        basal_items = [f"{p_product['product']}: {p_product['kg']} kg"]
        if rec_option[2]["kg"] > 0:
            basal_items.append(f"{rec_option[2]['product']}: {rec_option[2]['kg']} kg")
        if urea_basal > 0.05:
            basal_items.append(f"Urea: {round(urea_basal, 1)} kg")
        schedule = [
            {"when": "At sowing / transplanting (basal)", "day": 0, "items": basal_items,
             "note": "Mix into the soil near the seed rows, not touching the seed."},
            {"when": f"Top dressing 1 — around day {veg_day} (start of active growth)", "day": veg_day,
             "items": [f"Urea: {round(urea_rest / 2, 1)} kg"],
             "note": "Apply when soil is moist, after weeding. Do not apply before heavy rain."},
            {"when": f"Top dressing 2 — around day {flow_day} (before flowering)", "day": flow_day,
             "items": [f"Urea: {round(urea_rest / 2, 1)} kg"],
             "note": "Apply when soil is moist. Avoid getting urea on wet leaves."},
        ]

    return {
        "available": True,
        "source": source,
        "dose_per_ha": {"N": round(n, 1), "P2O5": round(p, 1), "K2O": round(k, 1)},
        "dose_for_plot_kg": {"N": round(need_n, 1), "P2O5": round(need_p, 1), "K2O": round(need_k, 1)},
        "soil_adjustments": adjustments,
        "option_a": {"title": "Option A: Urea + DAP + MOP", "items": option_a},
        "option_b": {"title": "Option B: Urea + SSP + MOP", "items": option_b, "sulphur_supplied_kg": sulphur_from_ssp},
        "recommended_option": "B" if prefer_b else "A",
        "why_option": why,
        "split_schedule": schedule,
        "notes": notes + [
            "Small plots may not need full bags. Many cooperative societies and dealers sell smaller packs; buy only what you need.",
            "General doses vary by state, variety and irrigation. If your Soil Health Card prints a fertilizer recommendation for your crop, enter it above — it replaces the general dose.",
        ],
    }


def _soil_amendments(crop_key: str, soil: Optional[dict], area_acres: float, prices: Optional[dict]) -> list:
    items = []
    ha = area_acres * HA_PER_ACRE
    zn, b, fe, ph = _num(soil, "Zn"), _num(soil, "B"), _num(soil, "Fe"), _num(soil, "pH")
    if zn is not None and zn < CRITICAL_LIMITS["Zn"]:
        items.append({
            "product": "Zinc sulphate (heptahydrate, 21% Zn)",
            "quantity": f"{round(ZINC_SULPHATE_KG_PER_HA * ha, 1)} kg for your plot",
            "why": f"Your zinc is {zn} mg/kg, below the critical level of {CRITICAL_LIMITS['Zn']} mg/kg.",
            "how": "Commonly applied to the soil before sowing, about 25 kg/ha, usually once every 2–3 seasons, not every season. Do not mix it with DAP or SSP in the same bag; apply separately.",
        })
    if b is not None and b < CRITICAL_LIMITS["B"]:
        items.append({
            "product": "Borax (boron fertilizer)",
            "quantity": "Very small dose — ask your KVK",
            "why": f"Your boron is {b} mg/kg, below the critical level of {CRITICAL_LIMITS['B']} mg/kg.",
            "how": "Boron is needed in tiny amounts and excess is harmful to crops, so use only the dose your Soil Health Card or KVK gives.",
        })
    if fe is not None and fe < CRITICAL_LIMITS["Fe"]:
        items.append({
            "product": "Ferrous sulphate (for iron deficiency)",
            "quantity": "Only if young leaves turn yellow — ask your KVK",
            "why": f"Your iron is {fe} mg/kg, below the critical level of {CRITICAL_LIMITS['Fe']} mg/kg.",
            "how": "Usually corrected with a foliar spray when symptoms appear. Adding organic manure also improves iron availability.",
        })
    if ph is not None and ph < 5.5:
        items.append({
            "product": "Agricultural lime",
            "quantity": "Based on a lime requirement test",
            "why": f"Your soil pH is {ph} (strongly acidic).",
            "how": "Ask the soil testing lab or KVK for a lime requirement test; the right amount depends on your soil.",
        })
    if ph is not None and ph > 8.5:
        items.append({
            "product": "Gypsum (for alkaline / sodic soil)",
            "quantity": "Based on a gypsum requirement test",
            "why": f"Your soil pH is {ph} (strongly alkaline).",
            "how": "Ask the soil testing lab or KVK for a gypsum requirement test before buying.",
        })
    if crop_key == "groundnut":
        items.append({
            "product": "Gypsum for groundnut",
            "quantity": "Ask your KVK for the dose",
            "why": "Groundnut needs calcium and sulphur in the top soil for well-filled pods.",
            "how": "Commonly applied near the plants at flowering / pegging time.",
        })
    return items


def _organic_and_bio(crop_key: str, profile: Optional[dict], area_acres: float) -> dict:
    fym_lo, fym_hi = (profile or {}).get("fym_tonnes_per_acre", (4, 6))
    lo, hi = round(fym_lo * area_acres, 1), round(fym_hi * area_acres, 1)
    category = CROP_PLANNING.get(crop_key, {}).get("category")
    if crop_key in LEGUMES:
        main_bio = BIOFERTILIZERS["legume"]
    elif category in ("cereal", "millet"):
        main_bio = BIOFERTILIZERS["cereal"]
    else:
        main_bio = BIOFERTILIZERS["other"]
    return {
        "manure": {
            "product": "Farmyard manure (FYM) or compost",
            "quantity": f"{lo}–{hi} tonnes for your plot (about {round((lo + hi) / 2 / 2, 1)} tractor trolleys)",
            "how": "Spread and mix into the soil 2–3 weeks before sowing. Vermicompost can replace part of it at a smaller quantity.",
        },
        "biofertilizers": [
            {"product": main_bio[0], "why": main_bio[1], "how": "Seed treatment just before sowing, as per the packet. Keep packets in shade."},
            {"product": BIOFERTILIZERS["all"][0], "why": BIOFERTILIZERS["all"][1], "how": "Seed or soil treatment, as per the packet."},
        ],
    }


def _plant_protection(crop_key: str, crop_result: Optional[dict]) -> dict:
    detected = None
    bio_groups = []
    if crop_result and crop_result.get("status") == "diseased":
        entry = DISEASE_BY_KEY.get(crop_result.get("disease_key") or "") or find_disease(crop_result.get("disease") or "")
        if entry:
            detected = {
                "name": entry["name"],
                "type": entry["type"],
                "urgency": entry["urgency"],
                "about": entry["about"],
                "actions": entry["actions"],
                "source": f"From your latest leaf check ({crop_result.get('crop')}, {round((crop_result.get('confidence') or 0) * 100)}% confidence)",
            }
            bio_groups += DISEASE_TYPE_TO_BIO.get(entry["type"], [])
            if entry["type"].startswith("oomycete") or entry["type"] == "fungal":
                bio_groups.append("fungal_leaf")

    pests = CROP_PESTS.get(crop_key, [])
    tools = []
    seen_tools = set()
    for pest, tool_key in pests:
        if tool_key in seen_tools:
            continue
        seen_tools.add(tool_key)
        t = MONITORING_TOOLS[tool_key]
        tools.append({"product": t["name"], "for": [p for p, k in pests if k == tool_key], "why": t["why"], "how": t["how"]})
        bio_groups.append("caterpillar" if tool_key in ("pheromone_trap", "bird_perch") else "sucking_pest")

    bio_groups.append("soil_borne")
    bio = []
    seen = set()
    for g in bio_groups:
        for name, why in BIO_OPTIONS.get(g, []):
            if name not in seen:
                seen.add(name)
                bio.append({"product": name, "why": why, "how": "Use as per the label / KVK advice. Works best early, before the problem becomes severe."})

    return {
        "detected_problem": detected,
        "common_pests": [p for p, _ in pests],
        "steps": [
            {"step": 1, "title": "Prevent with field practices (free)", "detail": "Healthy seed, correct spacing, crop rotation, removing infected plants and keeping the field clean prevent most problems."},
            {"step": 2, "title": "Monitor with low-cost traps", "detail": "Traps show you when pests start increasing, so you act early and only when needed."},
            {"step": 3, "title": "Use biological or neem-based products first", "detail": "They are safer for you, your soil and the natural enemies that eat pests."},
            {"step": 4, "title": "Registered chemical only if damage keeps increasing", "detail": "Go to a licensed dealer or your KVK with your crop name and the problem (show a photo or sample). Buy only a product whose label lists your crop and pest, and use exactly the label dose."},
        ],
        "monitoring_tools": tools,
        "bio_options": bio,
        "safety": PESTICIDE_SAFETY,
    }


def _weed_management(crop_key: str, profile: Optional[dict]) -> dict:
    duration = (profile or {}).get("duration_days", 110)
    critical_end = max(25, min(60, round(duration / 3)))
    planning = CROP_PLANNING.get(crop_key, {})
    vegetable = planning.get("category") == "vegetable"
    practices = [
        f"Keep the field weed-free for the first {critical_end} days after sowing — this is when weeds cause the most yield loss.",
        "Stale seedbed: water the prepared field (or wait for first rain), let weeds sprout for about a week, remove them by light ploughing, then sow.",
        "Hand weeding or a hand hoe / wheel hoe between rows around day 20–25 and again around day 40–45.",
    ]
    if vegetable:
        practices.append("Mulching with straw or dry leaves between rows suppresses weeds and saves water.")
    return {
        "critical_weed_free_days": critical_end,
        "practices": practices,
        "tools_to_buy": ["Hand hoe or khurpi", "Wheel hoe (for line-sown crops)"] + (["Straw or plastic mulch"] if vegetable else []),
        "herbicide_note": (
            "Herbicides are crop-specific: a herbicide meant for one crop can kill another. Pre-emergence herbicides "
            "are applied soon after sowing on moist soil before weeds come up; post-emergence ones after weeds appear. "
            "If hand weeding is not possible, ask your KVK which herbicide is registered for your crop, and use the label dose."
        ),
    }


def recommend_inputs(
    crop_name: str,
    area_acres: Optional[float] = 1.0,
    soil: Optional[dict] = None,
    crop_result: Optional[dict] = None,
    shc_npk: Optional[dict] = None,
    prices: Optional[dict] = None,
) -> dict:
    crop_key, profile = get_crop_profile(crop_name)
    acres = float(area_acres) if area_acres and area_acres > 0 else 1.0
    display = profile["name"] if profile else crop_name

    fert = build_fertilizer_plan(crop_key, profile, acres, soil, shc_npk, prices)
    amendments = _soil_amendments(crop_key, soil, acres, prices)
    organic = _organic_and_bio(crop_key, profile, acres)
    protection = _plant_protection(crop_key, crop_result)
    weeds = _weed_management(crop_key, profile)

    shopping = []
    total = 0.0
    priced_any = False
    if fert.get("available"):
        opt = fert["option_b"] if fert["recommended_option"] == "B" else fert["option_a"]
        for line in opt["items"]:
            if line["kg"] <= 0:
                continue
            shopping.append({
                "category": "Fertilizer",
                "item": line["product"],
                "quantity": f"{line['kg']} kg ({line['bags_exact']} bags of {line['bag_kg']} kg; buy {line['bags_to_buy']})",
                "cost": line["estimated_cost"],
            })
            if line["estimated_cost"] is not None:
                total += line["estimated_cost"]
                priced_any = True
    for a in amendments:
        shopping.append({"category": "Soil correction", "item": a["product"], "quantity": a["quantity"], "cost": None})
    shopping.append({"category": "Organic", "item": organic["manure"]["product"], "quantity": organic["manure"]["quantity"], "cost": None})
    for bf in organic["biofertilizers"]:
        shopping.append({"category": "Bio-fertilizer", "item": bf["product"], "quantity": "As per packet for your plot", "cost": None})
    for t in protection["monitoring_tools"]:
        shopping.append({"category": "Pest monitoring", "item": t["product"], "quantity": "As per pack / KVK advice for your plot size", "cost": None})
    for b in protection["bio_options"][:3]:
        shopping.append({"category": "Bio-protection (buy when needed)", "item": b["product"], "quantity": "Only if problem appears; label dose", "cost": None})
    for tool in weeds["tools_to_buy"]:
        shopping.append({"category": "Weeding", "item": tool, "quantity": "1", "cost": None})

    return {
        "crop": display,
        "crop_key": crop_key,
        "area_acres": round(acres, 2),
        "area_guntas": round(acres * 40, 1),
        "fertilizer_plan": fert,
        "soil_amendments": amendments,
        "organic_and_bio": organic,
        "plant_protection": protection,
        "weed_management": weeds,
        "shopping_list": shopping,
        "estimated_fertilizer_cost": round(total, 0) if priced_any else None,
        "where_to_buy": WHERE_TO_BUY,
        "disclaimer": (
            "Fertilizer quantities are calculated from a general or Soil-Health-Card dose and the nutrient content of "
            "standard fertilizers. This app never recommends a specific chemical pesticide or herbicide; those must be "
            "chosen with a licensed dealer or KVK for your crop and used exactly as the label says."
        ),
    }
