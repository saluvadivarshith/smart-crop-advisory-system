"""
Farmer Advisory Engine.

Translates technical outputs from the crop model, soil service, weather service,
and integrated risk engine into clear, practical, low-cost recommendations
for small and marginal farmers.

Safety guarantee:
  * Never invents pesticide names, chemical dosages, or fertilizer quantities.
  * Prioritizes field scouting, sanitation, irrigation timing, organic matter,
    and consulting the local Krishi Vigyan Kendra (KVK) or agriculture officer.
"""

from typing import Optional

from backend.knowledge.diseases import DISEASE_BY_KEY, GENERIC_BY_TYPE, find_disease


def generate_advisory(
    crop_name: Optional[str] = None,
    growth_stage: Optional[str] = None,
    crop_result: Optional[dict] = None,
    soil_result: Optional[dict] = None,
    weather_result: Optional[dict] = None,
    risk_result: Optional[dict] = None,
) -> dict:
    """Build a structured, plain-language farmer advisory."""
    crop_label = (
        (risk_result or {}).get("crop")
        or crop_name
        or (crop_result or {}).get("crop")
        or "Crop"
    )
    risk_level = (risk_result or {}).get("risk_level", "UNKNOWN")
    risk_score = (risk_result or {}).get("risk_score")

    # 1. Determine headline problem
    crop_status = (crop_result or {}).get("status")
    disease_name = (crop_result or {}).get("disease")
    disease_key = (crop_result or {}).get("disease_key")
    disease_entry = (
        DISEASE_BY_KEY.get(disease_key)
        if disease_key
        else find_disease(disease_name or "")
    )

    if crop_status == "diseased" and disease_name:
        possible_problem = f"Possible {disease_name} on {crop_label}"
    elif crop_status == "uncertain":
        possible_problem = f"Uncertain leaf symptoms on {crop_label} (clearer photo needed)"
    elif crop_status == "healthy":
        if risk_level in {"HIGH", "MODERATE"}:
            possible_problem = f"{crop_label} leaves look healthy, but soil or weather needs attention"
        else:
            possible_problem = f"{crop_label} appears healthy with low current risk"
    else:
        if (soil_result or {}).get("problems") and (weather_result or {}).get("rain_alerts"):
            possible_problem = f"Soil nutrient stress and heavy rain risk for {crop_label}"
        elif (soil_result or {}).get("problems"):
            possible_problem = f"Soil nutrient deficiency detected for {crop_label}"
        elif risk_level in {"HIGH", "MODERATE"}:
            possible_problem = f"Weather-related crop stress risk for {crop_label}"
        else:
            possible_problem = f"General advisory for {crop_label}"

    # 2. Recommended farmer actions (prioritized, practical, low-cost)
    actions = []

    def add_action(title: str, detail: str, priority: str = "normal", category: str = "general"):
        actions.append({
            "step": len(actions) + 1,
            "title": title,
            "detail": detail,
            "priority": priority,
            "category": category,
        })

    # Crop / disease actions
    if crop_status == "uncertain":
        add_action(
            "Retake a clear close-up leaf photograph",
            "Hold the phone steady in natural daylight, focus on a single affected leaf against a plain background, and re-upload.",
            priority="high",
            category="crop",
        )
        add_action(
            "Inspect 10–15 nearby plants in your field",
            "Check both upper and lower leaf surfaces across different corners of the field to see if symptoms are spreading.",
            priority="high",
            category="crop",
        )
    elif crop_status == "diseased":
        if disease_entry:
            for idx, act_text in enumerate(disease_entry["actions"]):
                add_action(
                    act_text.split(".")[0] + ".",
                    act_text,
                    priority="high" if idx < 2 else "normal",
                    category="crop",
                )
        else:
            for act_text in GENERIC_BY_TYPE["fungal"]["actions"]:
                add_action(act_text.split(".")[0] + ".", act_text, priority="high", category="crop")
    elif crop_status == "healthy":
        add_action(
            "Continue weekly field scouting",
            "Walk through the field once or twice a week, checking older lower leaves and new shoots for early spots or pests.",
            priority="normal",
            category="crop",
        )

    # Soil actions
    soil_attention = []
    if soil_result and soil_result.get("available"):
        for param in soil_result.get("parameters", []):
            if param["severity"] in {"problem", "attention"}:
                soil_attention.append({
                    "parameter": param["label"],
                    "value": f"{param['value']} {param['unit']}".strip(),
                    "status": param["status_label"],
                    "why_it_matters": param["why_it_matters"],
                    "next_step": param["next_step"],
                })
        problem_params = [p for p in soil_result.get("parameters", []) if p["severity"] == "problem"]
        for p in problem_params[:3]:
            add_action(
                f"Address {p['label']} ({p['status_label']})",
                p["next_step"],
                priority="high" if p["parameter"] in {"N", "P", "K", "pH", "OC"} else "normal",
                category="soil",
            )
    else:
        soil_attention.append({
            "parameter": "Soil Health Card",
            "value": "Not provided",
            "status": "Unavailable",
            "why_it_matters": "Knowing soil pH, organic carbon, and nutrient levels prevents wasted fertilizer spend.",
            "next_step": "Enter values from your Government Soil Health Card, or visit your nearest soil testing lab / KVK.",
        })

    # Weather, irrigation, and spray-window actions
    weather_summary = None
    if weather_result and "current" in weather_result:
        cur = weather_result["current"]
        irr = weather_result.get("irrigation") or {}
        windows = weather_result.get("spray_windows") or []
        rain_alerts = weather_result.get("rain_alerts") or []

        if rain_alerts:
            add_action(
                "Prepare field drainage before heavy rain",
                f"Heavy rain ({rain_alerts[0]['precipitation_sum']} mm) is forecast on {rain_alerts[0]['date']}. Clear drainage channels to prevent waterlogging and root rot.",
                priority="high",
                category="weather",
            )

        if irr.get("advice"):
            add_action(
                "Plan irrigation using 3-day water balance",
                f"{irr['advice']} (3-day forecast rain: {irr.get('rain_next_3_days_mm', 0)} mm vs. ET₀ water loss: {irr.get('et0_next_3_days_mm', 0)} mm).",
                priority="normal",
                category="weather",
            )

        if windows:
            w0 = windows[0]
            add_action(
                "Use suitable weather window for any foliar field work",
                f"Next low-wind, rain-free daytime window: {w0['start'].replace('T', ' ')} to {w0['end'].replace('T', ' ')} "
                f"(max wind {w0['max_wind_kmh']} km/h, max temp {w0['max_temp_c']}°C).",
                priority="normal",
                category="weather",
            )
        elif crop_status == "diseased":
            add_action(
                "Avoid spraying during wind or expected rain",
                "No ideal spray window was found in the next 48 hours due to wind, heat, or rain risk. Wait for calm, rain-free morning/evening hours.",
                priority="normal",
                category="weather",
            )

        weather_summary = {
            "current_conditions": (
                f"{cur.get('description', 'Current')}: {cur.get('temperature')}°C, "
                f"Humidity {cur.get('humidity')}%, Wind {cur.get('wind_speed')} km/h"
            ),
            "irrigation_advice": irr.get("advice"),
            "next_spray_window": (
                f"{windows[0]['start'].replace('T', ' ')} – {windows[0]['end'].replace('T', ' ')}"
                if windows
                else "No suitable window in next 48h"
            ),
            "rain_alerts": rain_alerts,
        }

    # Always include expert consultation / safety step when risk is moderate/high or disease is present
    if risk_level in {"HIGH", "MODERATE"} or crop_status in {"diseased", "uncertain"}:
        add_action(
            "Consult your local KVK or Agriculture Officer before chemical application",
            "Take affected leaf samples and your Soil Health Card to your local Krishi Vigyan Kendra (KVK) or Rythu Bharosa / Raitha Samparka Kendra for locally approved product and dosage advice. You can also call the Kisan Call Centre (toll-free 1800-180-1551).",
            priority="high" if risk_level == "HIGH" else "normal",
            category="safety",
        )

    why_this_warning = (risk_result or {}).get("reasons") or [
        "Advisory generated from the information provided."
    ]

    # Build a clean plain-text summary suitable for Text-to-Speech (TTS) or WhatsApp sharing
    tts_lines = [
        f"Advisory for {crop_label}.",
        f"Overall risk level is {risk_level}." if risk_level != "UNKNOWN" else "",
        f"Main finding: {possible_problem}.",
        "Why this warning: " + " ".join(why_this_warning[:3]),
        "Recommended next steps: " + " ".join(f"Step {a['step']}: {a['title']}" for a in actions[:4]),
    ]
    plain_text_summary = " ".join(x for x in tts_lines if x)

    return {
        "crop": crop_label,
        "growth_stage": growth_stage,
        "possible_problem": possible_problem,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "why_this_warning": why_this_warning,
        "recommended_actions": actions,
        "soil_attention": soil_attention,
        "weather_summary": weather_summary,
        "plain_text_summary": plain_text_summary,
        "helpline": {
            "name": "Kisan Call Centre (Govt. of India)",
            "phone": "1800-180-1551",
            "note": "Toll-free, 6 AM to 10 PM, available in regional languages.",
        },
        "disclaimer": (
            "AI predictions and rule-based advisories are for decision support only and do not replace "
            "certified agricultural extension officers or laboratory testing. Never apply pesticides or "
            "fertilizers without verifying crop-specific dosages with your local KVK."
        ),
    }
