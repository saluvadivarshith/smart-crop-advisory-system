"""
Crop leaf image analysis service.

Handles file validation, image quality inspection, ML model inference,
Grad-CAM visual attention heatmap generation, uncertainty estimation,
crop-mismatch detection, and a 1-click sample leaf gallery from PlantVillage.
"""

import base64
import io
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from backend.knowledge.crops import get_crop_profile, normalize_crop
from backend.knowledge.diseases import DISEASE_BY_KEY, find_disease
from backend.ml.labels import parse_class_name
from backend.ml.predict import predictor
from backend.ml.preprocess import image_quality, load_image
from backend.utils.validators import ValidationError, validate_image_upload

DEFAULT_CONFIDENCE_THRESHOLD = 0.55
MIN_MARGIN_THRESHOLD = 0.12

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PLANTVILLAGE_COLOR_DIR = WORKSPACE_ROOT / "plantvillage dataset" / "color"
BUNDLED_SAMPLES_DIR = WORKSPACE_ROOT / "backend" / "ml" / "sample_leaves"


def _get_samples_root() -> Optional[Path]:
    if PLANTVILLAGE_COLOR_DIR.is_dir():
        return PLANTVILLAGE_COLOR_DIR
    if BUNDLED_SAMPLES_DIR.is_dir():
        return BUNDLED_SAMPLES_DIR
    return None

# Curated showcase classes from PlantVillage for the 1-Click Sample Gallery
SHOWCASE_SAMPLE_FOLDERS = [
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___healthy",
    "Potato___Late_blight",
    "Potato___Early_blight",
    "Pepper,_bell___Bacterial_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Apple___Black_rot",
    "Grape___Black_rot",
    "Orange___Haunglongbing_(Citrus_greening)",
]


def _estimate_foliage_ratio(img) -> float:
    """Estimate fraction of pixels that look like plant foliage (green/yellow/brown leaf tones)."""
    small = img.copy()
    small.thumbnail((256, 256))
    arr = np.asarray(small, dtype=np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    greenish = (g > r * 0.85) & (g > b * 1.05) & (g > 0.12)
    yellow_brown = (r > 0.20) & (g > 0.15) & (b < 0.45) & (r >= b * 1.2) & (g >= b * 1.1)
    mask = greenish | yellow_brown
    return round(float(mask.mean()), 3)


def get_model_status() -> dict:
    """Return current ML model readiness and evaluation metrics if available."""
    if not predictor.is_available():
        return {
            "available": False,
            "model_path": str(predictor.model_path),
            "message": (
                "Trained model weights not found at backend/ml/model/crop_disease_model.pt. "
                "Run `python -m backend.ml.train --data-dir \"plantvillage dataset\"` to train the model."
            ),
        }
    try:
        meta = predictor.metadata
        supported_crops = sorted({c["crop_name"] for c in meta.get("classes", [])})
        return {
            "available": True,
            "arch": meta.get("arch"),
            "num_classes": len(meta.get("class_names", [])),
            "supported_crops": supported_crops,
            "classes": meta.get("classes", []),
            "best_val_accuracy": meta.get("best_val_accuracy"),
            "test_accuracy": meta.get("test_accuracy"),
            "confidence_threshold": meta.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD),
            "trained_at": meta.get("trained_at"),
            "dataset": meta.get("dataset"),
            "split_sizes": meta.get("split_sizes"),
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "message": "Model file exists but could not be loaded.",
        }


def _first_image_in(folder: Path) -> Optional[Path]:
    if not folder.is_dir():
        return None
    try:
        candidates = []
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in {".jpg", ".jpeg", ".png"}:
                    candidates.append(entry.name)
                    if len(candidates) >= 6:
                        break
        if not candidates:
            return None
        candidates.sort()
        # Pick index 1 when available (in PlantVillage, index 0 in Tomato___Early_blight is an edge-cropped leaf)
        chosen = candidates[1] if len(candidates) > 1 else candidates[0]
        return folder / chosen
    except OSError:
        return None


def get_sample_leaf_gallery() -> list[dict]:
    """Return a list of real PlantVillage sample leaf cards with compact thumbnails."""
    samples_root = _get_samples_root()
    if not samples_root:
        return []

    supported_classes = set()
    if predictor.is_available():
        try:
            supported_classes = set(predictor.metadata.get("class_names", []))
        except Exception:
            supported_classes = set()

    samples = []
    for folder_name in SHOWCASE_SAMPLE_FOLDERS:
        if supported_classes and folder_name not in supported_classes:
            continue
        folder_path = samples_root / folder_name
        img_path = _first_image_in(folder_path)
        if not img_path:
            continue
        try:
            with Image.open(img_path) as im:
                thumb = im.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            thumb.save(buf, format="JPEG", quality=78)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            info = parse_class_name(folder_name)
            samples.append({
                "class_folder": folder_name,
                "crop_name": info["crop_name"],
                "crop_key": info["crop_key"],
                "disease_name": info["disease_name"],
                "healthy": info["healthy"],
                "filename": img_path.name,
                "thumbnail_uri": f"data:image/jpeg;base64,{b64}",
            })
        except OSError:
            continue
    return samples


def analyze_sample_leaf(class_folder: str) -> dict:
    """Run full ML + Grad-CAM analysis on a sample leaf from PlantVillage."""
    safe_name = Path(class_folder).name
    samples_root = _get_samples_root() or BUNDLED_SAMPLES_DIR
    folder_path = samples_root / safe_name
    img_path = _first_image_in(folder_path)
    if not img_path:
        raise ValidationError(f"Sample class '{safe_name}' was not found in dataset or bundled samples.")
    info = parse_class_name(safe_name)
    data = img_path.read_bytes()
    return analyze_crop_image(
        filename=img_path.name,
        content_type="image/jpeg",
        data=data,
        selected_crop=info["crop_name"],
    )


def analyze_crop_image(
    filename: str,
    content_type: Optional[str],
    data: bytes,
    selected_crop: Optional[str] = None,
) -> dict:
    """Validate and analyze an uploaded crop leaf image, including Grad-CAM heatmap."""
    file_info = validate_image_upload(filename, content_type, data)
    img = load_image(data)
    quality = image_quality(img)
    foliage_ratio = _estimate_foliage_ratio(img)

    if foliage_ratio < 0.08:
        quality["warnings"].append(
            "Very little leaf or plant tissue was detected in the frame. Please photograph a single leaf closely against a plain background."
        )
        quality["ok"] = False

    selected_key = normalize_crop(selected_crop) if selected_crop else None
    _, selected_profile = get_crop_profile(selected_key) if selected_key else (None, None)

    if not predictor.is_available():
        return {
            "available": False,
            "status": "model_not_trained",
            "filename": file_info["filename"],
            "image_info": file_info,
            "quality": quality,
            "foliage_ratio": foliage_ratio,
            "selected_crop": selected_profile["name"] if selected_profile else selected_crop,
            "crop": None,
            "disease": None,
            "confidence": None,
            "is_healthy": None,
            "is_uncertain": True,
            "top_predictions": [],
            "message": (
                "The image was validated and preprocessed, but the disease classification model "
                "has not been trained yet."
            ),
        }

    meta = predictor.metadata
    classes_meta = meta.get("classes") or [parse_class_name(c) for c in meta["class_names"]]
    supported_crop_keys = {c["crop_key"] for c in classes_meta}
    supported_crop_names = sorted({c["crop_name"] for c in classes_meta})

    if selected_key and selected_key not in supported_crop_keys:
        return {
            "available": True,
            "status": "unsupported_crop",
            "filename": file_info["filename"],
            "image_info": file_info,
            "quality": quality,
            "foliage_ratio": foliage_ratio,
            "selected_crop": selected_profile["name"] if selected_profile else selected_crop,
            "supported_crops": supported_crop_names,
            "crop": selected_profile["name"] if selected_profile else selected_crop,
            "disease": None,
            "confidence": None,
            "is_healthy": None,
            "is_uncertain": True,
            "top_predictions": [],
            "message": (
                f"Leaf disease image classification is currently trained for {', '.join(supported_crop_names)}. "
                f"'{selected_crop}' is not yet supported by the image model, though soil, weather, and crop calendar advisory remain available."
            ),
        }

    cam_out = predictor.predict_with_gradcam(
        img,
        top_k=3,
        selected_crop_key=selected_key if (selected_key in supported_crop_keys) else None,
    )
    top_raw = cam_out["top_pairs"]

    top_predictions = []
    for idx, prob in top_raw:
        c_info = classes_meta[idx]
        top_predictions.append({
            "class_name": c_info["class_name"],
            "crop_key": c_info["crop_key"],
            "crop_name": c_info["crop_name"],
            "disease_key": c_info["disease_key"],
            "disease_name": c_info["disease_name"],
            "healthy": c_info["healthy"],
            "confidence": round(prob, 4),
        })

    best = top_predictions[0]
    second_conf = top_predictions[1]["confidence"] if len(top_predictions) > 1 else 0.0
    margin = best["confidence"] - second_conf
    threshold = float(meta.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD))

    uncertainty_reasons = []
    if best["confidence"] < threshold:
        uncertainty_reasons.append(
            f"Model confidence ({best['confidence'] * 100:.1f}%) is below the reliability threshold ({threshold * 100:.0f}%)."
        )
    if margin < 0.06 and len(top_predictions) > 1 and best["confidence"] < 0.65:
        uncertainty_reasons.append(
            f"The top two possibilities ({best['crop_name']} {best['disease_name']} vs. "
            f"{top_predictions[1]['crop_name']} {top_predictions[1]['disease_name']}) have close scores."
        )

    crop_mismatch = bool(selected_key and best["crop_key"] != selected_key)
    is_uncertain = bool(uncertainty_reasons)
    disease_entry = (
        DISEASE_BY_KEY.get(best["disease_key"])
        if best.get("disease_key")
        else find_disease(best.get("disease_name", ""))
    )

    if is_uncertain:
        status = "uncertain"
        explanation = (
            "The model could not make a high-confidence diagnosis from this photograph. "
            + " ".join(uncertainty_reasons)
            + " Please take a clear, well-lit close-up photo of a single affected leaf."
        )
    elif best["healthy"]:
        status = "healthy"
        explanation = (
            f"The {best['crop_name']} leaf appears healthy ({best['confidence'] * 100:.1f}% confidence). "
            "No visible foliar disease symptoms were detected in this photograph. Continue regular field scouting."
        )
    else:
        status = "diseased"
        about = disease_entry["about"] if disease_entry else "Visible leaf symptoms detected."
        explanation = (
            f"Possible {best['disease_name']} detected on {best['crop_name']} "
            f"({best['confidence'] * 100:.1f}% model confidence). {about}"
        )

    return {
        "available": True,
        "status": status,
        "filename": file_info["filename"],
        "image_info": file_info,
        "quality": quality,
        "foliage_ratio": foliage_ratio,
        "selected_crop": selected_profile["name"] if selected_profile else selected_crop,
        "crop": best["crop_name"],
        "crop_key": best["crop_key"],
        "disease": "Healthy" if best["healthy"] else best["disease_name"],
        "disease_key": best["disease_key"],
        "disease_type": disease_entry["type"] if disease_entry else ("healthy" if best["healthy"] else None),
        "confidence": best["confidence"],
        "confidence_threshold": threshold,
        "is_healthy": bool(best["healthy"] and not is_uncertain),
        "is_uncertain": is_uncertain,
        "crop_mismatch": crop_mismatch,
        "uncertainty_reasons": uncertainty_reasons,
        "top_predictions": top_predictions,
        "original_data_uri": cam_out["original_data_uri"],
        "gradcam_data_uri": cam_out["gradcam_data_uri"],
        "hotspot_coverage_pct": cam_out["hotspot_coverage_pct"],
        "explanation": explanation,
        "message": explanation,
        "disclaimer": (
            "Advisory image screening only — not a laboratory diagnosis. "
            "The Grad-CAM heatmap highlights the leaf areas that most influenced the neural network."
        ),
    }
