"""
FastAPI backend for the Smart Crop Advisory System for Small and Marginal Farmers.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database.database import init_db
from backend.database.models import (
    create_assessment,
    create_farm,
    delete_assessment,
    delete_farm,
    get_assessment,
    get_farm,
    list_assessments,
    list_farms,
    update_farm,
)
from backend.knowledge.crops import CROP_PROFILES, GROWTH_STAGES
from backend.schemas import (
    AdvisoryRequest,
    CalendarRequest,
    FarmCreate,
    InputsRecommendRequest,
    NewFarmPlanRequest,
    SampleLeafRequest,
    SoilData,
    SoilTextParseRequest,
)
from backend.services.advisory_service import generate_advisory
from backend.services.calendar_service import get_crop_calendar, parse_soil_card_text
from backend.services.crop_service import (
    analyze_crop_image,
    analyze_sample_leaf,
    get_model_status,
    get_sample_leaf_gallery,
)
from backend.services.inputs_service import recommend_inputs
from backend.services.location_service import GeocodingError, reverse_geocode, search_location
from backend.services.new_farm_service import recommend_new_farm_plan
from backend.services.risk_service import evaluate_risk
from backend.services.soil_service import analyze_soil
from backend.services.weather_service import WeatherServiceError, get_weather
from backend.utils.validators import ValidationError, validate_coordinates


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Smart Crop Advisory API",
    description=(
        "Multimodal decision-support API for small and marginal farmers: "
        "leaf disease classification, Soil Health Card interpretation, "
        "farm-specific weather intelligence, explainable risk fusion, and practical advisory."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Home & Health
# -------------------------

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Smart Crop Advisory Backend is running",
        "docs_url": "/docs",
        "frontend_url": "/app/",
    }


@app.get("/health")
def health():
    model_info = get_model_status()
    return {
        "status": "healthy",
        "ml_model_ready": model_info.get("available", False),
    }


# -------------------------
# Reference Crops & Metadata
# -------------------------

@app.get("/api/crops")
def get_supported_crops():
    model_info = get_model_status()
    ml_crops = set(model_info.get("supported_crops", []))
    crops = []
    for key, profile in CROP_PROFILES.items():
        crops.append({
            "key": key,
            "name": profile["name"],
            "preferred_ph": profile["ph"],
            "salt_tolerance": profile["salt"],
            "ml_image_supported": profile["name"] in ml_crops,
        })
    return {
        "crops": crops,
        "growth_stages": GROWTH_STAGES,
        "ml_supported_crops": sorted(ml_crops),
    }


# -------------------------
# Location & Geocoding API
# -------------------------

@app.get("/api/location/search")
def location_search(
    q: str = Query(..., min_length=2, max_length=120, description="Village, town, mandal, or district name"),
    country: str = Query("in", max_length=4),
):
    try:
        results = search_location(q, country_code=country)
        return {"query": q, "count": len(results), "results": results}
    except GeocodingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/location/reverse")
def location_reverse(
    latitude: float = Query(..., description="Latitude (-90 to 90)"),
    longitude: float = Query(..., description="Longitude (-180 to 180)"),
):
    try:
        lat, lon = validate_coordinates(latitude, longitude)
        return reverse_geocode(lat, lon)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GeocodingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# -------------------------
# Farm Profile CRUD API
# -------------------------

@app.get("/api/farms")
def api_list_farms():
    farms = list_farms()
    return {"count": len(farms), "farms": farms}


@app.post("/api/farms", status_code=201)
def api_create_farm(farm: FarmCreate):
    return create_farm(farm.model_dump())


@app.get("/api/farms/{farm_id}")
def api_get_farm(farm_id: int):
    farm = get_farm(farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found.")
    return farm


@app.put("/api/farms/{farm_id}")
def api_update_farm(farm_id: int, farm: FarmCreate):
    updated = update_farm(farm_id, farm.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found.")
    return updated


@app.delete("/api/farms/{farm_id}")
def api_delete_farm(farm_id: int):
    if not delete_farm(farm_id):
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found.")
    return {"deleted": True, "id": farm_id}


# -------------------------
# Soil Analysis API
# -------------------------

@app.post("/api/soil/analyze")
def soil_analysis(data: SoilData):
    payload = data.model_dump()
    crop_name = payload.pop("crop", None)
    return analyze_soil(payload, crop_name=crop_name)


@app.post("/api/soil/parse-text")
def soil_parse_text(req: SoilTextParseRequest):
    return parse_soil_card_text(req.text)


@app.post("/api/crop/calendar")
def api_crop_calendar(req: CalendarRequest):
    return get_crop_calendar(
        crop_name=req.crop_name,
        sowing_date_str=req.sowing_date,
        current_stage=req.growth_stage,
        area_acres=req.area_acres,
        weather_result=req.weather_result,
    )


@app.post("/api/new-farm/plan")
def api_new_farm_plan(req: NewFarmPlanRequest):
    return recommend_new_farm_plan(
        season=req.season,
        water_source=req.water_source,
        budget=req.budget,
        labour=req.labour,
        area_acres=req.area_acres,
        soil_ph=req.soil_ph,
        soil_ec=req.soil_ec,
        soil_n=req.soil_n,
        selected_crop=req.selected_crop,
    )


@app.post("/api/inputs/recommend")
def api_inputs_recommend(req: InputsRecommendRequest):
    return recommend_inputs(
        crop_name=req.crop_name,
        area_acres=req.area_acres,
        soil=req.soil_values,
        crop_result=req.crop_result,
        shc_npk=req.shc_npk,
        prices=req.prices,
    )


# -------------------------
# Weather API
# -------------------------

@app.get("/api/weather")
def weather(
    latitude: float = Query(..., description="Farm latitude (-90 to 90)"),
    longitude: float = Query(..., description="Farm longitude (-180 to 180)"),
):
    try:
        lat, lon = validate_coordinates(latitude, longitude)
        return get_weather(lat, lon)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WeatherServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# -------------------------
# Crop Image Analysis API
# -------------------------

@app.get("/api/crop/model-info")
def crop_model_info():
    return get_model_status()


@app.get("/api/crop/samples")
def crop_samples():
    samples = get_sample_leaf_gallery()
    return {"count": len(samples), "samples": samples}


@app.post("/api/crop/analyze-sample")
def crop_analyze_sample(req: SampleLeafRequest):
    try:
        return analyze_sample_leaf(req.class_folder)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/crop/analyze")
def crop_analysis(
    image: UploadFile = File(...),
    crop: Optional[str] = Form(default=None),
):
    try:
        raw_bytes = image.file.read()
        return analyze_crop_image(
            filename=image.filename or "upload.jpg",
            content_type=image.content_type,
            data=raw_bytes,
            selected_crop=crop,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# -------------------------
# Risk & Advisory Engine API
# -------------------------

@app.post("/api/risk/evaluate")
def api_evaluate_risk(req: AdvisoryRequest):
    soil_res = req.soil_result
    if soil_res is None and req.soil_data is not None:
        sd = req.soil_data.model_dump()
        c_name = sd.pop("crop", None) or req.crop_name
        soil_res = analyze_soil(sd, crop_name=c_name)

    weather_res = req.weather_result
    if weather_res is None and req.latitude is not None and req.longitude is not None:
        try:
            weather_res = get_weather(req.latitude, req.longitude)
        except WeatherServiceError:
            weather_res = None

    return evaluate_risk(
        crop_name=req.crop_name,
        growth_stage=req.growth_stage,
        crop_result=req.crop_result,
        soil_result=soil_res,
        weather_result=weather_res,
    )


@app.post("/api/advisory/generate")
def api_generate_advisory(req: AdvisoryRequest):
    soil_res = req.soil_result
    if soil_res is None and req.soil_data is not None:
        sd = req.soil_data.model_dump()
        c_name = sd.pop("crop", None) or req.crop_name
        soil_res = analyze_soil(sd, crop_name=c_name)

    weather_res = req.weather_result
    if weather_res is None and req.latitude is not None and req.longitude is not None:
        try:
            weather_res = get_weather(req.latitude, req.longitude)
        except WeatherServiceError:
            weather_res = None

    risk_res = evaluate_risk(
        crop_name=req.crop_name,
        growth_stage=req.growth_stage,
        crop_result=req.crop_result,
        soil_result=soil_res,
        weather_result=weather_res,
    )

    advisory_res = generate_advisory(
        crop_name=req.crop_name,
        growth_stage=req.growth_stage,
        crop_result=req.crop_result,
        soil_result=soil_res,
        weather_result=weather_res,
        risk_result=risk_res,
    )

    calendar_res = get_crop_calendar(
        crop_name=req.crop_name,
        sowing_date_str=req.sowing_date,
        current_stage=req.growth_stage,
        area_acres=req.area_acres,
        weather_result=weather_res,
    )

    saved_record = None
    if req.save_to_history and risk_res.get("available"):
        crop_res = req.crop_result or {}
        compact_weather = None
        if weather_res and "current" in weather_res:
            compact_weather = {
                "current": weather_res.get("current"),
                "daily": (weather_res.get("daily") or [])[:3],
                "irrigation": weather_res.get("irrigation"),
                "spray_windows": (weather_res.get("spray_windows") or [])[:2],
            }
        # Strip large base64 images before saving JSON to SQLite history
        clean_crop_res = {
            k: v for k, v in crop_res.items() if k not in {"original_data_uri", "gradcam_data_uri"}
        }
        saved_record = create_assessment({
            "farm_id": req.farm_id,
            "crop_name": risk_res.get("crop") or req.crop_name,
            "growth_stage": req.growth_stage,
            "image_filename": clean_crop_res.get("filename"),
            "predicted_disease": clean_crop_res.get("disease"),
            "model_confidence": clean_crop_res.get("confidence"),
            "crop_status": clean_crop_res.get("status"),
            "soil_score": (soil_res or {}).get("soil_score"),
            "soil_data": soil_res,
            "weather_data": compact_weather,
            "risk_score": risk_res.get("risk_score"),
            "risk_level": risk_res.get("risk_level"),
            "advisory": advisory_res,
            "details": risk_res,
        })

    return {
        "risk": risk_res,
        "advisory": advisory_res,
        "soil": soil_res,
        "calendar": calendar_res,
        "saved_assessment": saved_record,
    }


# -------------------------
# Assessment History API
# -------------------------

@app.get("/api/assessments")
def api_list_assessments(
    farm_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    items = list_assessments(farm_id=farm_id, limit=limit)
    return {"count": len(items), "assessments": items}


@app.get("/api/assessments/{assessment_id}")
def api_get_assessment(assessment_id: int):
    record = get_assessment(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")
    return record


@app.delete("/api/assessments/{assessment_id}")
def api_delete_assessment(assessment_id: int):
    if not delete_assessment(assessment_id):
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")
    return {"deleted": True, "id": assessment_id}


# Serve the frontend directory at /app so users can open http://127.0.0.1:8000/app/
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
