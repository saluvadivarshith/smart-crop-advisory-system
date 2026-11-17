"""
End-to-end automated tests for the Smart Crop Advisory System backend.
Tests all API handlers, Pydantic schemas, SQLite persistence, image validation,
soil analysis, risk engine, and advisory engine.
"""

import asyncio
import io
import os
import tempfile

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageDraw
from pydantic import ValidationError as PydanticValidationError
from starlette.datastructures import Headers

# Use an isolated temporary SQLite database for tests
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["CROP_ADVISORY_DB"] = _tmp_db.name

from backend.database.database import init_db
from backend.main import (
    api_create_farm,
    api_delete_assessment,
    api_delete_farm,
    api_generate_advisory,
    api_get_assessment,
    api_list_assessments,
    api_list_farms,
    crop_analysis,
    get_supported_crops,
    health,
    home,
    soil_analysis,
)
from backend.ml.labels import parse_class_name
from backend.schemas import AdvisoryRequest, FarmCreate, SoilData

init_db()


def _make_leaf_image_bytes(width=256, height=256, fmt="JPEG") -> bytes:
    """Create a sharp green leaf-like image for upload pipeline testing."""
    img = Image.new("RGB", (width, height), (35, 65, 30))
    draw = ImageDraw.Draw(img)
    draw.polygon([(30, 128), (128, 30), (225, 128), (128, 225)], fill=(55, 145, 50), outline=(25, 90, 25))
    for offset in range(50, 200, 20):
        draw.line([(40, offset), (210, offset + 10)], fill=(120, 190, 80), width=2)
        draw.ellipse((offset, 100, offset + 12, 112), fill=(135, 85, 35), outline=(60, 35, 15))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_upload(filename: str, data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_health_and_home():
    assert home()["status"] == "online"
    assert health()["status"] == "healthy"
    crops_resp = get_supported_crops()
    assert len(crops_resp["crops"]) >= 10


def test_label_parser_variants():
    c1 = parse_class_name("Tomato___Early_blight")
    assert c1["crop_key"] == "tomato"
    assert c1["disease_key"] == "early_blight"
    assert not c1["healthy"]

    c2 = parse_class_name("Pepper,_bell___healthy")
    assert c2["crop_key"] == "pepper"
    assert c2["healthy"] is True

    c3 = parse_class_name("Potato___Late_blight")
    assert c3["crop_key"] == "potato"
    assert c3["disease_key"] == "late_blight"


def test_soil_analysis_full_partial_and_empty():
    # 1. Empty card -> gracefully explains soil analysis is unavailable
    d_empty = soil_analysis(SoilData(crop="Tomato"))
    assert d_empty["available"] is False
    assert d_empty["soil_score"] is None

    # 2. Deficient card
    d_def = soil_analysis(
        SoilData(
            crop="Tomato",
            N=180,
            P=8,
            K=95,
            OC=0.35,
            pH=8.1,
            EC=0.6,
            Zn=0.4,
        )
    )
    assert d_def["available"] is True
    assert d_def["soil_score"] < 60
    assert any("Nitrogen" in p for p in d_def["problems"])
    assert any("Zinc" in p for p in d_def["problems"])

    # 3. Invalid negative nitrogen or impossible pH -> Pydantic validation error
    with pytest.raises(PydanticValidationError):
        SoilData(N=-50, pH=19.0)


def test_crop_upload_validation():
    # 1. Unsupported file extension (.txt)
    with pytest.raises(HTTPException) as exc1:
        crop_analysis(_make_upload("notes.txt", b"hello world", "text/plain"), crop="Tomato")
    assert exc1.value.status_code == 400
    assert "Unsupported file format" in exc1.value.detail

    # 2. Corrupted image bytes with .jpg extension
    with pytest.raises(HTTPException) as exc2:
        crop_analysis(_make_upload("leaf.jpg", b"not_a_jpeg_at_all", "image/jpeg"), crop="Tomato")
    assert exc2.value.status_code == 400
    assert "not a valid image" in exc2.value.detail

    # 3. Tiny image (< 64x64)
    tiny_buf = io.BytesIO()
    Image.new("RGB", (32, 32), (0, 200, 0)).save(tiny_buf, format="PNG")
    with pytest.raises(HTTPException) as exc3:
        crop_analysis(_make_upload("tiny.png", tiny_buf.getvalue(), "image/png"), crop="Tomato")
    assert exc3.value.status_code == 400
    assert "too small" in exc3.value.detail

    # 4. Valid leaf image upload
    valid_bytes = _make_leaf_image_bytes()
    body = crop_analysis(_make_upload("leaf.jpg", valid_bytes, "image/jpeg"), crop="Tomato")
    assert body["filename"] == "leaf.jpg"
    assert body["status"] in {"healthy", "diseased", "uncertain", "model_not_trained", "unsupported_crop"}


def test_farm_crud_and_assessment_history():
    # Create farm with land dimensions and map polygon boundary
    polygon_coords = [
        [18.1930, 79.7025],
        [18.1930, 79.7035],
        [18.1920, 79.7035],
        [18.1920, 79.7025],
    ]
    farm = api_create_farm(
        FarmCreate(
            farm_name="Raju Plot 1",
            village="Parkal",
            district="Hanamkonda",
            state="Telangana",
            latitude=18.1925,
            longitude=79.7031,
            crop_name="Tomato",
            area_acres=2.85,
            plot_length_m=110.0,
            plot_width_m=105.0,
            boundary_geojson=polygon_coords,
        )
    )
    farm_id = farm["id"]
    assert farm["farm_name"] == "Raju Plot 1"
    assert farm["plot_length_m"] == 110.0
    assert farm["plot_width_m"] == 105.0
    assert farm["boundary_geojson"] == polygon_coords

    # List farms
    farms_list = api_list_farms()
    assert any(f["id"] == farm_id for f in farms_list["farms"])

    # Generate integrated advisory & save to SQLite
    mock_crop_result = {
        "available": True,
        "status": "diseased",
        "filename": "tomato_leaf.jpg",
        "crop": "Tomato",
        "crop_key": "tomato",
        "disease": "Early Blight",
        "disease_key": "early_blight",
        "confidence": 0.91,
        "is_healthy": False,
        "is_uncertain": False,
    }
    mock_weather_result = {
        "current": {
            "temperature": 26.0,
            "humidity": 89,
            "wind_speed": 8.0,
            "description": "Overcast",
        },
        "daily": [
            {
                "date": "2026-11-05",
                "temp_max": 28.0,
                "temp_min": 21.0,
                "precipitation_sum": 12.0,
                "precipitation_probability_max": 80,
                "et0_mm": 3.5,
                "humid_hours": 14,
            }
        ],
        "hourly_next_72h": [
            {"time": f"2026-11-05T{h:02d}:00", "temperature_2m": 24.0, "relative_humidity_2m": 90}
            for h in range(16)
        ],
        "irrigation": {
            "status": "rain_sufficient",
            "rain_next_3_days_mm": 18.0,
            "et0_next_3_days_mm": 10.5,
            "water_deficit_mm": 0.0,
            "advice": "Forecast rain covers expected water loss.",
        },
        "spray_windows": [
            {"start": "2026-11-06T08:00", "end": "2026-11-06T11:00", "hours": 3, "max_wind_kmh": 7.5, "max_temp_c": 26.5}
        ],
        "rain_alerts": [],
    }

    adv_payload = api_generate_advisory(
        AdvisoryRequest(
            farm_id=farm_id,
            crop_name="Tomato",
            growth_stage="flowering",
            crop_result=mock_crop_result,
            soil_data=SoilData(N=190, P=18, K=180, OC=0.4, pH=6.5, EC=0.4),
            weather_result=mock_weather_result,
            save_to_history=True,
        )
    )
    assert adv_payload["risk"]["risk_level"] == "HIGH"
    assert adv_payload["risk"]["risk_score"] >= 65
    assert len(adv_payload["advisory"]["recommended_actions"]) >= 4
    saved_id = adv_payload["saved_assessment"]["id"]

    # Retrieve assessment history
    hist = api_list_assessments(farm_id=farm_id, limit=50)
    assert hist["count"] >= 1

    detail = api_get_assessment(saved_id)
    assert detail["predicted_disease"] == "Early Blight"

    # Cleanup
    assert api_delete_assessment(saved_id)["deleted"] is True
    assert api_delete_farm(farm_id)["deleted"] is True


def test_ml_dataset_splits_and_predictor(tmp_path):
    """Verify dataset discovery, stratified splitting, and CropDiseasePredictor inference."""
    import torch
    from backend.ml.dataset import build_splits
    from backend.ml.model_def import build_model
    from backend.ml.predict import CropDiseasePredictor

    # Create a tiny temporary PlantVillage-structured dataset (2 classes, 10 images each)
    for cls_name in ("Tomato___Early_blight", "Tomato___healthy"):
        cls_dir = tmp_path / cls_name
        cls_dir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            (cls_dir / f"img_{i}.jpg").write_bytes(_make_leaf_image_bytes(128, 128))

    class_names, train, val, test = build_splits(tmp_path, crops=["tomato"])
    assert class_names == ["Tomato___Early_blight", "Tomato___healthy"]
    assert len(train) + len(val) + len(test) == 20

    # Save a checkpoint and run inference via CropDiseasePredictor
    model = build_model("mobilenet_v3_small", num_classes=2, pretrained=False)
    ckpt_path = tmp_path / "test_model.pt"
    torch.save(
        {
            "state_dict": model.state_dict(),
            "arch": "mobilenet_v3_small",
            "class_names": class_names,
            "classes": [parse_class_name(c) for c in class_names],
            "img_size": 224,
            "confidence_threshold": 0.70,
        },
        ckpt_path,
    )

    pred = CropDiseasePredictor(model_path=ckpt_path)
    assert pred.is_available() is True
    img = Image.open(io.BytesIO(_make_leaf_image_bytes()))
    top = pred.predict(img, top_k=2)
    assert len(top) == 2
    assert abs(sum(p for _, p in top) - 1.0) < 1e-4

    # Verify Grad-CAM explainability output
    gcam = pred.predict_with_gradcam(img, top_k=2)
    assert len(gcam["top_pairs"]) == 2
    assert gcam["original_data_uri"].startswith("data:image/jpeg;base64,")
    assert gcam["gradcam_data_uri"].startswith("data:image/jpeg;base64,")
    assert 0.0 <= gcam["hotspot_coverage_pct"] <= 100.0


def test_soil_scanner_and_crop_calendar():
    """Verify Smart Soil Report Text Scanner and Crop Stage Calendar."""
    from backend.services.calendar_service import get_crop_calendar, parse_soil_card_text

    sample_sms = (
        "Soil Health Card: pH: 7.8 | EC: 0.58 dS/m | Organic Carbon (OC): 0.39% | "
        "Available N: 192 kg/ha | Phosphorus (P): 15.5 kg/ha | Potassium (K): 168 kg/ha | "
        "Sulphur (S): 8.4 ppm | Zinc (Zn): 0.46 ppm | Iron (Fe): 4.2 ppm | Boron (B): 0.41 ppm"
    )
    parsed = parse_soil_card_text(sample_sms)
    assert parsed["extracted_count"] >= 9
    assert parsed["values"]["pH"] == 7.8
    assert parsed["values"]["N"] == 192.0
    assert parsed["values"]["Zn"] == 0.46

    cal = get_crop_calendar(
        crop_name="Tomato",
        sowing_date_str="2026-09-25",
        current_stage="flowering",
        area_acres=2.5,
        weather_result={"irrigation": {"water_deficit_mm": 12.0, "rain_next_3_days_mm": 2.0, "et0_next_3_days_mm": 14.0}},
    )
    assert cal["crop"] == "Tomato"
    assert cal["plot_area"]["acres"] == 2.5
    assert cal["plot_area"]["guntas"] == 100.0
    assert len(cal["timeline"]) >= 4
    assert cal["water_balance_plot"]["net_deficit_liters"] > 0
    assert cal["organic_manure_guide"]["fym_tonnes_max"] > 0


def test_new_farm_plan_and_inputs_advisor():
    """Verify 'Start a New Farm' wizard and 'What to Buy' fertilizer/IPM advisor."""
    from backend.services.inputs_service import recommend_inputs
    from backend.services.new_farm_service import recommend_new_farm_plan

    plan = recommend_new_farm_plan(
        season="rabi",
        water_source="limited",
        budget="low",
        labour="family",
        area_acres=1.5,
        soil_ph=6.8,
        soil_ec=0.45,
        soil_n=210.0,
    )
    assert plan["season"]["key"] == "rabi"
    assert len(plan["recommended_crops"]) >= 5
    assert len(plan["selected_crop_plan"]["pre_sowing_checklist"]) == 6
    assert len(plan["schemes_and_help"]) >= 5

    inp = recommend_inputs(
        crop_name="Tomato",
        area_acres=2.0,
        soil={"N": 190, "P": 16, "K": 180, "S": 8.0, "Zn": 0.45, "pH": 6.8},
        prices={"urea": 266, "dap": 1350, "ssp": 550, "mop": 1700},
    )
    assert inp["crop"] == "Tomato"
    assert inp["area_acres"] == 2.0
    assert inp["fertilizer_plan"]["available"] is True
    assert inp["fertilizer_plan"]["recommended_option"] == "B"  # Sulphur is low (<10 mg/kg)
    assert inp["estimated_fertilizer_cost"] > 0
    assert len(inp["shopping_list"]) >= 5


