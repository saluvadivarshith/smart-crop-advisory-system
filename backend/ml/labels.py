"""
Convert dataset folder names (e.g. ``Tomato___Early_blight``) into a crop and
disease that the rest of the application understands.

Works with the common PlantVillage variants on Kaggle:
  * "Tomato___Early_blight", "Pepper,_bell___healthy", "Corn_(maize)___Common_rust_"
  * "Tomato_Early_blight", "Pepper__bell___Bacterial_spot", "Tomato__Target_Spot"
"""

import re

from backend.knowledge.crops import get_crop_profile, normalize_crop
from backend.knowledge.diseases import find_disease

# Used when a folder name has no "___" separator.
KNOWN_CROP_PREFIXES = [
    "pepper__bell", "pepper_bell", "pepper,_bell", "corn_(maize)", "cherry_(including_sour)",
    "tomato", "potato", "pepper", "corn", "maize", "apple", "grape", "orange", "peach",
    "strawberry", "squash", "soybean", "blueberry", "raspberry", "cherry", "rice", "wheat",
    "cotton", "chilli", "groundnut",
]


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse_class_name(folder_name):
    raw = folder_name.strip()
    lower = raw.lower()

    if "___" in raw:
        crop_part, disease_part = raw.split("___", 1)
    else:
        crop_part, disease_part = None, None
        for prefix in sorted(KNOWN_CROP_PREFIXES, key=len, reverse=True):
            if lower.startswith(prefix):
                crop_part, disease_part = raw[:len(prefix)], raw[len(prefix):]
                break
        if crop_part is None:
            crop_part, _, disease_part = raw.partition("_")

    crop_clean = re.sub(r"\(.*?\)", "", crop_part.lower()).replace(",", " ")
    crop_clean = re.sub(r"[\s_]+", "_", crop_clean).strip("_")
    crop_key = normalize_crop(crop_clean)

    disease_slug = _slug(disease_part)
    # Drop a repeated crop name, e.g. "tomato_yellowleaf_curl_virus".
    for token in {crop_key, crop_clean.split("_")[0]}:
        if token and disease_slug.startswith(token + "_"):
            disease_slug = disease_slug[len(token) + 1:]

    healthy = disease_slug == "healthy" or disease_slug.endswith("healthy")
    entry = None if healthy else find_disease(disease_slug)

    _, profile = get_crop_profile(crop_key)
    crop_name = profile["name"] if profile else crop_key.replace("_", " ").title()

    if healthy:
        disease_name = "Healthy"
    elif entry:
        disease_name = entry["name"]
    else:
        disease_name = disease_slug.replace("_", " ").strip().capitalize()

    return {
        "class_name": raw,
        "crop_key": crop_key,
        "crop_name": crop_name,
        "disease_slug": "healthy" if healthy else disease_slug,
        "disease_key": entry["key"] if entry else None,
        "disease_name": disease_name,
        "healthy": healthy,
    }
