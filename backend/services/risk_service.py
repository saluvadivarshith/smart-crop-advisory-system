"""
Integrated Crop Risk Engine.

Combines four sources of evidence into a transparent, explainable risk
assessment:
  1. Crop leaf image analysis (disease urgency and confidence state)
  2. Soil Health Card analysis (deficiencies, pH / salinity stress)
  3. Farm-specific weather (disease-conducive hours, heat/cold/rain stress)
  4. Crop type and growth stage sensitivity

Design principles:
  * Never adds unrelated percentages (e.g. ML confidence + humidity %) together.
  * Never treats ML softmax confidence as a probability of yield loss.
  * Uses explicit, documented rule points with a human-readable breakdown
    so farmers and examiners can see why the risk is LOW, MODERATE, or HIGH.
  * Works gracefully when only 1 or 2 modalities are provided.
"""

from typing import Optional

from backend.knowledge.crops import get_crop_profile
from backend.knowledge.diseases import DISEASE_BY_KEY, GENERIC_BY_TYPE, find_disease

# Growth stages where foliar disease or weather stress has greater yield impact
SENSITIVE_STAGES = {"flowering", "fruiting", "seedling"}


def _count_favorable_hours(hourly: list[dict], rule: dict) -> int:
    """Count hours in the next 72h forecast matching the disease's microclimate rule."""
    if not hourly or not rule:
        return 0
    t_min = rule.get("temp_min", -50)
    t_max = rule.get("temp_max", 60)
    rh_min = rule.get("rh_min")
    rh_max = rule.get("rh_max")

    count = 0
    for h in hourly:
        temp = h.get("temperature_2m")
        rh = h.get("relative_humidity_2m")
        if temp is None or rh is None:
            continue
        if not (t_min <= temp <= t_max):
            continue
        if rh_min is not None and rh < rh_min:
            continue
        if rh_max is not None and rh > rh_max:
            continue
        count += 1
    return count


def _score_crop_component(crop_result: Optional[dict]) -> dict:
    """Evaluate risk points (0-45) from the crop image analysis."""
    if not crop_result or not crop_result.get("available"):
        return {
            "available": False,
            "points": 0,
            "max_points": 45,
            "level": "unavailable",
            "reasons": [],
            "disease_entry": None,
        }

    status = crop_result.get("status")
    if status in {"model_not_trained", "unsupported_crop"}:
        return {
            "available": False,
            "points": 0,
            "max_points": 45,
            "level": status,
            "reasons": [],
            "disease_entry": None,
        }

    if status == "healthy":
        return {
            "available": True,
            "points": 5,
            "max_points": 45,
            "level": "low",
            "reasons": [f"Leaf photograph looks healthy ({crop_result.get('crop')})."],
            "disease_entry": None,
        }

    disease_key = crop_result.get("disease_key")
    disease_name = crop_result.get("disease") or "Possible symptom"
    entry = DISEASE_BY_KEY.get(disease_key) if disease_key else find_disease(disease_name)

    if status == "uncertain":
        return {
            "available": True,
            "points": 18,
            "max_points": 45,
            "level": "uncertain",
            "reasons": [
                f"Leaf image result is uncertain (top candidate: {disease_name}). Field inspection is needed."
            ],
            "disease_entry": entry,
        }

    # Confirmed high-confidence symptom prediction
    urgency = entry["urgency"] if entry else "moderate"
    if urgency == "high":
        pts = 38
        lvl = "high"
    elif urgency == "moderate":
        pts = 28
        lvl = "moderate"
    else:
        pts = 20
        lvl = "low"

    return {
        "available": True,
        "points": pts,
        "max_points": 45,
        "level": lvl,
        "reasons": [
            f"Leaf symptoms consistent with {disease_name} ({urgency} urgency {entry['type'] if entry else 'condition'})."
        ],
        "disease_entry": entry,
    }


def _score_weather_component(
    weather_result: Optional[dict],
    crop_profile: Optional[dict],
    disease_entry: Optional[dict],
) -> dict:
    """Evaluate risk points (0-30) from farm weather and disease-weather interaction."""
    if not weather_result or "current" not in weather_result:
        return {
            "available": False,
            "points": 0,
            "max_points": 30,
            "level": "unavailable",
            "reasons": [],
            "favorable_hours": 0,
        }

    hourly = weather_result.get("hourly_next_72h") or []
    daily = weather_result.get("daily") or []
    current = weather_result.get("current") or {}

    points = 0
    reasons = []

    # 1. Disease-specific or general fungal microclimate check
    rule = (disease_entry or {}).get("weather")
    if not rule:
        rule = GENERIC_BY_TYPE["fungal"]["weather"]

    fav_hours = _count_favorable_hours(hourly, rule)
    h_high = rule.get("hours_high", 12)
    h_mod = rule.get("hours_moderate", 6)

    if fav_hours >= h_high:
        points += 18
        if disease_entry:
            reasons.append(
                f"Forecast shows {fav_hours} hours in the next 3 days with {rule['text']}, which strongly favors {disease_entry['name']} spread."
            )
        else:
            reasons.append(
                f"Forecast shows {fav_hours} humid hours ({rule['text']}) over the next 3 days, which favors fungal leaf diseases."
            )
    elif fav_hours >= h_mod:
        points += 10
        reasons.append(
            f"Forecast shows {fav_hours} hours of {rule['text']} in the next 3 days, moderately favorable for disease development."
        )
    elif (current.get("humidity") or 0) >= 85:
        points += 8
        reasons.append(f"Current relative humidity is high ({current['humidity']}%), increasing leaf wetness.")

    # 2. Heavy rainfall / waterlogging / splash dispersal check
    rain_alerts = weather_result.get("rain_alerts") or []
    max_rain_prob = max(((d.get("precipitation_probability_max") or 0) for d in daily[:3]), default=0)
    rain_3d = sum((d.get("precipitation_sum") or 0) for d in daily[:3])

    if rain_alerts:
        points += 10
        reasons.append(
            f"Heavy rainfall alert ({rain_alerts[0]['precipitation_sum']} mm forecast on {rain_alerts[0]['date']}); risk of waterlogging and rain-splash disease spread."
        )
    elif rain_3d >= 25 or max_rain_prob >= 75:
        points += 6
        reasons.append(
            f"Significant rain expected in the next 3 days ({rain_3d:.1f} mm, up to {max_rain_prob}% probability)."
        )

    # 3. Crop-specific temperature stress
    if crop_profile and daily:
        max_t = max((d.get("temp_max") for d in daily[:3] if d.get("temp_max") is not None), default=None)
        min_t = min((d.get("temp_min") for d in daily[:3] if d.get("temp_min") is not None), default=None)
        if max_t is not None and max_t > crop_profile["heat_tmax"]:
            points += 6
            reasons.append(
                f"Forecast high of {max_t}°C exceeds {crop_profile['name']} heat stress threshold ({crop_profile['heat_tmax']}°C). {crop_profile['heat_note']}"
            )
        if min_t is not None and min_t < crop_profile["cold_tmin"]:
            points += 6
            reasons.append(
                f"Forecast low of {min_t}°C drops below {crop_profile['name']} cold threshold ({crop_profile['cold_tmin']}°C)."
            )

    points = min(points, 30)
    if points >= 18:
        lvl = "high"
    elif points >= 10:
        lvl = "moderate"
    else:
        lvl = "low"
        if not reasons:
            reasons.append("Weather conditions over the next 3 days look generally favorable.")

    return {
        "available": True,
        "points": points,
        "max_points": 30,
        "level": lvl,
        "reasons": reasons,
        "favorable_hours": fav_hours,
    }


def _score_soil_component(soil_result: Optional[dict]) -> dict:
    """Evaluate risk points (0-25) from Soil Health Card analysis."""
    if not soil_result or not soil_result.get("available"):
        return {
            "available": False,
            "points": 0,
            "max_points": 25,
            "level": "unavailable",
            "reasons": [],
        }

    problems = soil_result.get("problems") or []
    attention = soil_result.get("attention") or []
    score = soil_result.get("soil_score") or 100

    if not problems and not attention:
        return {
            "available": True,
            "points": 2,
            "max_points": 25,
            "level": "low",
            "reasons": [f"Soil health index is {score}/100 with no major deficiencies detected."],
        }

    points = min(25, len(problems) * 6 + len(attention) * 2)
    if score < 50:
        points = max(points, 18)
    elif score < 70:
        points = max(points, 10)

    reasons = []
    if problems:
        reasons.append(f"Soil deficiencies / stresses identified: {', '.join(problems)}.")
    if attention and not problems:
        reasons.append(f"Soil parameters needing attention: {', '.join(attention)}.")

    lvl = "high" if points >= 16 else ("moderate" if points >= 8 else "low")
    return {
        "available": True,
        "points": points,
        "max_points": 25,
        "level": lvl,
        "reasons": reasons,
    }


def evaluate_risk(
    crop_name: Optional[str] = None,
    growth_stage: Optional[str] = None,
    crop_result: Optional[dict] = None,
    soil_result: Optional[dict] = None,
    weather_result: Optional[dict] = None,
) -> dict:
    """Combine available evidence into an explainable risk score and category."""
    effective_crop = (
        crop_name
        or (crop_result or {}).get("selected_crop")
        or (crop_result or {}).get("crop")
        or (soil_result or {}).get("crop")
        or "General Crop"
    )
    _, profile = get_crop_profile(effective_crop)

    crop_comp = _score_crop_component(crop_result)
    weather_comp = _score_weather_component(weather_result, profile, crop_comp.get("disease_entry"))
    soil_comp = _score_soil_component(soil_result)

    active_max = (
        (crop_comp["max_points"] if crop_comp["available"] else 0)
        + (weather_comp["max_points"] if weather_comp["available"] else 0)
        + (soil_comp["max_points"] if soil_comp["available"] else 0)
    )
    raw_points = crop_comp["points"] + weather_comp["points"] + soil_comp["points"]

    interaction_bonus = 0
    interaction_reasons = []

    # Compound risk 1: Active disease + conducive weather
    if (
        crop_comp["available"]
        and (crop_result or {}).get("status") == "diseased"
        and weather_comp["available"]
        and weather_comp["level"] in {"moderate", "high"}
    ):
        interaction_bonus += 10
        interaction_reasons.append(
            "Compound risk: Active leaf disease symptoms combined with disease-favorable weather can accelerate spread."
        )

    # Compound risk 2: Active disease + soil nutrient stress weakens plant defense
    if (
        crop_comp["available"]
        and (crop_result or {}).get("status") == "diseased"
        and soil_comp["available"]
        and soil_comp["level"] in {"moderate", "high"}
    ):
        interaction_bonus += 5
        interaction_reasons.append(
            "Compound risk: Soil nutrient imbalance can weaken crop recovery from leaf infection."
        )

    # Compound risk 3: Sensitive growth stage (flowering / fruiting / seedling)
    stage_norm = (growth_stage or "").strip().lower()
    if stage_norm in SENSITIVE_STAGES and raw_points >= 20:
        interaction_bonus += 5
        interaction_reasons.append(
            f"Crop is at the sensitive '{stage_norm}' stage, where stress has a stronger impact on yield."
        )

    if active_max == 0:
        return {
            "available": False,
            "crop": profile["name"] if profile else effective_crop,
            "growth_stage": growth_stage,
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "reasons": ["No crop image, soil card, or weather data was provided yet."],
            "components": {},
            "modalities_used": [],
        }

    # Normalize against active modalities, then add compound interaction bonus
    normalized = round(100.0 * raw_points / active_max)
    risk_score = min(100, normalized + interaction_bonus)

    # Safety floor rules:
    # A high-urgency disease (e.g. Late Blight, Yellow Leaf Curl Virus) is never LOW risk
    disease_entry = crop_comp.get("disease_entry")
    if (crop_result or {}).get("status") == "diseased":
        if disease_entry and disease_entry.get("urgency") == "high":
            if weather_comp.get("level") in {"moderate", "high"}:
                risk_score = max(risk_score, 75)
            else:
                risk_score = max(risk_score, 62)
        else:
            risk_score = max(risk_score, 45)

    if risk_score >= 65:
        risk_level = "HIGH"
    elif risk_score >= 35:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    reasons = (
        crop_comp["reasons"]
        + weather_comp["reasons"]
        + soil_comp["reasons"]
        + interaction_reasons
    )

    modalities_used = []
    if crop_comp["available"]:
        modalities_used.append("leaf_image")
    if soil_comp["available"]:
        modalities_used.append("soil_health_card")
    if weather_comp["available"]:
        modalities_used.append("weather_forecast")

    missing_modalities = []
    if not crop_comp["available"]:
        missing_modalities.append("crop leaf photo")
    if not soil_comp["available"]:
        missing_modalities.append("Soil Health Card values")
    if not weather_comp["available"]:
        missing_modalities.append("farm weather forecast")

    return {
        "available": True,
        "crop": profile["name"] if profile else effective_crop,
        "growth_stage": growth_stage,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reasons": reasons,
        "interaction_reasons": interaction_reasons,
        "modalities_used": modalities_used,
        "missing_modalities": missing_modalities,
        "completeness_note": (
            f"Assessment uses {len(modalities_used)} of 3 inputs ({', '.join(modalities_used)}). "
            f"Add {' and '.join(missing_modalities)} for a more complete assessment."
            if missing_modalities
            else "Complete 3-way assessment (leaf image + Soil Health Card + farm weather)."
        ),
        "components": {
            "crop_disease": {
                "available": crop_comp["available"],
                "points": crop_comp["points"],
                "max_points": crop_comp["max_points"],
                "level": crop_comp["level"],
            },
            "weather": {
                "available": weather_comp["available"],
                "points": weather_comp["points"],
                "max_points": weather_comp["max_points"],
                "level": weather_comp["level"],
                "favorable_hours_next_72h": weather_comp["favorable_hours"],
            },
            "soil": {
                "available": soil_comp["available"],
                "points": soil_comp["points"],
                "max_points": soil_comp["max_points"],
                "level": soil_comp["level"],
            },
        },
        "disclaimer": (
            "Prototype rule-based risk index combining leaf symptom urgency, soil ratings, and 72-hour "
            "weather forecast. It is an decision-support indicator, not a statistical prediction of yield loss."
        ),
    }
