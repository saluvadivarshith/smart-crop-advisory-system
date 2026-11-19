"""
FastAPI backend for the Smart Crop Advisory System for Small and Marginal Farmers.
"""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
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
    AuthCheckRequest,
    AuthResendOtpRequest,
    AuthSenderConfigRequest,
    AuthSigninRequest,
    AuthSignupRequest,
    AuthVerifyOtpRequest,
    CalendarRequest,
    CropAdvisoryCreate,
    FarmCreate,
    GoogleIdTokenRequest,
    InputsRecommendRequest,
    NewFarmPlanRequest,
    PhoneCompleteSignupRequest,
    PhoneStartOtpRequest,
    PrePasswordOtpStartRequest,
    SampleLeafRequest,
    SoilData,
    SoilTextParseRequest,
)
from backend.services.advisory_service import generate_advisory
from backend.services.auth_service import (
    AuthError,
    check_account_exists,
    complete_phone_signup_with_password,
    complete_pre_password_signup,
    get_sender_settings,
    get_user_by_token,
    logout_token,
    resend_otp_challenge,
    save_sender_settings,
    signin_user,
    signin_with_google_id_token,
    signup_user,
    start_phone_pre_password_otp,
    start_pre_password_otp,
    verify_otp_challenge,
    verify_phone_pre_password_otp,
    verify_pre_password_otp,
)
from backend.services.calendar_service import get_crop_calendar, parse_soil_card_text
from backend.services.crop_service import (
    analyze_crop_image,
    analyze_sample_leaf,
    get_model_status,
    get_sample_leaf_gallery,
)
from backend.services.inputs_service import recommend_inputs
from backend.services.insforge_service import (
    InsForgeAuthError,
    InsForgeDBError,
    extract_bearer_token,
    get_insforge_config,
    insforge_create_assessment,
    insforge_create_crop_advisory,
    insforge_create_farm,
    insforge_delete_assessment,
    insforge_delete_crop_advisory,
    insforge_delete_farm,
    insforge_get_assessment,
    insforge_get_farm,
    insforge_list_assessments,
    insforge_list_crop_advisories,
    insforge_list_farms,
    insforge_update_farm,
    is_insforge_configured,
    verify_insforge_token,
)
from backend.services.location_service import GeocodingError, reverse_geocode, search_location
from backend.services.new_farm_service import recommend_new_farm_plan
from backend.services.risk_service import evaluate_risk
from backend.services.soil_service import analyze_soil
from backend.services.supabase_service import (
    SupabaseAuthError,
    get_supabase_config,
    is_supabase_configured,
    verify_supabase_token,
)
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


@app.middleware("http")
async def no_cache_frontend(request, call_next):
    if request.url.path == "/" and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/app/")
    response = await call_next(request)
    if request.url.path.startswith("/app"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


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
# Farmer Authentication API (Email & Phone Sign-Up / Sign-In)
# -------------------------

@app.post("/api/auth/check")
def api_auth_check(req: AuthCheckRequest):
    try:
        return check_account_exists(req.identifier)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/auth/signup", status_code=201)
def api_auth_signup(req: AuthSignupRequest):
    try:
        return signup_user(
            full_name=req.full_name,
            password=req.password,
            email=req.email,
            phone=req.phone,
            preferred_channel=req.preferred_channel,
            require_otp=True,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/signin")
def api_auth_signin(req: AuthSigninRequest):
    try:
        return signin_user(identifier=req.identifier, password=req.password, require_otp=True)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/verify-otp")
def api_auth_verify_otp(req: AuthVerifyOtpRequest):
    try:
        return verify_otp_challenge(challenge_id=req.challenge_id, otp_code=req.otp_code)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/resend-otp")
def api_auth_resend_otp(req: AuthResendOtpRequest):
    try:
        return resend_otp_challenge(challenge_id=req.challenge_id)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/auth/sender-settings")
def api_get_sender_settings():
    info = get_sender_settings()
    return {
        "smtp_email": info["smtp_email"],
        "smtp_configured": info["smtp_configured"],
        "sms_configured": info["sms_configured"],
    }


@app.post("/api/auth/sender-settings")
def api_save_sender_settings(req: AuthSenderConfigRequest):
    return save_sender_settings(
        smtp_email=req.smtp_email,
        smtp_app_password=req.smtp_app_password,
        fast2sms_api_key=req.fast2sms_api_key,
    )


@app.get("/api/config/supabase")
def api_supabase_public_config():
    """Return ONLY public Supabase Auth config (URL + publishable key) from .env.local."""
    cfg = get_supabase_config()
    return {
        "configured": is_supabase_configured(),
        "url": cfg["url"],
        "publishableKey": cfg["publishableKey"],
    }


@app.get("/api/config/insforge")
def api_insforge_public_config():
    """Return public InsForge client config when InsForge mode is active."""
    cfg = get_insforge_config()
    return {
        "configured": is_insforge_configured(),
        "baseUrl": cfg["baseUrl"],
        "anonKey": cfg["anonKey"],
    }


def _resolve_user_auth(authorization: Optional[str], required: bool = True) -> dict:
    """
    Resolve the signed-in user from `Authorization: Bearer <token>`.
    - Supabase JWT tokens are verified via `GET {SUPABASE_URL}/auth/v1/user`
      and mapped to a per-user local SQLite record for localhost isolation.
    - InsForge JWT tokens (when InsForge cloud mode is active) enable RLS CRUD.
    - Local phone/email session tokens are verified against SQLite (`mode='local'`).
    """
    raw_token = extract_bearer_token(authorization)
    if raw_token:
        # JWT tokens have 3 dot-separated segments
        if raw_token.count(".") == 2:
            if is_supabase_configured():
                try:
                    sb_user = verify_supabase_token(authorization)
                    return {"mode": "local", "provider": "supabase", "user": sb_user, "token": raw_token}
                except SupabaseAuthError as exc:
                    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            if is_insforge_configured():
                try:
                    user = verify_insforge_token(authorization)
                    return {"mode": "insforge", "provider": "insforge", "user": user, "token": user["access_token"]}
                except InsForgeAuthError as exc:
                    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

        local_user = get_user_by_token(authorization)
        if local_user:
            return {"mode": "local", "provider": "local", "user": local_user, "token": raw_token}
        raise HTTPException(status_code=401, detail="Invalid or expired session token. Please sign in again.")

    if os.environ.get("INSFORGE_USE_LOCAL_SQLITE") == "1" or not is_insforge_configured():
        return {"mode": "local", "provider": "local", "user": None, "token": None}

    if required:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in to create or view your farm records.",
        )
    return {"mode": "anonymous", "provider": None, "user": None, "token": None}


@app.post("/api/auth/phone/start")
def api_auth_phone_start(req: PhoneStartOtpRequest):
    try:
        return start_phone_pre_password_otp(phone=req.phone, full_name=req.full_name)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/phone/verify")
def api_auth_phone_verify(req: AuthVerifyOtpRequest):
    try:
        return verify_phone_pre_password_otp(challenge_id=req.challenge_id, otp_code=req.otp_code)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/phone/complete", status_code=201)
def api_auth_phone_complete(req: PhoneCompleteSignupRequest):
    try:
        return complete_phone_signup_with_password(
            verification_token=req.verification_token,
            password=req.password,
            full_name=req.full_name,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/otp/start")
def api_auth_otp_start(req: PrePasswordOtpStartRequest):
    try:
        return start_pre_password_otp(identifier=req.identifier, full_name=req.full_name)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/otp/verify")
def api_auth_otp_verify(req: AuthVerifyOtpRequest):
    try:
        return verify_pre_password_otp(challenge_id=req.challenge_id, otp_code=req.otp_code)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/auth/otp/complete", status_code=201)
def api_auth_otp_complete(req: PhoneCompleteSignupRequest):
    try:
        return complete_pre_password_signup(
            verification_token=req.verification_token,
            password=req.password,
            full_name=req.full_name,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/auth/me")
def api_auth_me(authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    if not ctx["user"]:
        raise HTTPException(status_code=401, detail="Not signed in or session expired.")
    return {"authenticated": True, "provider": ctx["mode"], "user": ctx["user"]}


@app.post("/api/auth/logout")
def api_auth_logout(authorization: Optional[str] = Header(default=None)):
    logout_token(authorization)
    return {"logged_out": True}


# -------------------------
# Farm Profile CRUD API (User-Owned via InsForge RLS / Scoped SQLite)
# -------------------------

@app.get("/api/farms")
def api_list_farms(authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] == "insforge":
        try:
            farms = insforge_list_farms(ctx["token"])
            return {"count": len(farms), "farms": farms, "source": "insforge"}
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    uid = ctx["user"]["id"] if ctx["user"] else None
    farms = list_farms(user_id=uid)
    return {"count": len(farms), "farms": farms, "source": "sqlite"}


@app.post("/api/farms", status_code=201)
def api_create_farm(farm: FarmCreate, authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    payload = farm.model_dump()
    if ctx["mode"] == "insforge":
        try:
            return insforge_create_farm(ctx["token"], payload)
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    payload["user_id"] = ctx["user"]["id"] if ctx["user"] else None
    return create_farm(payload)


@app.get("/api/farms/{farm_id}")
def api_get_farm(farm_id: str, authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] == "insforge":
        try:
            farm = insforge_get_farm(ctx["token"], farm_id)
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    else:
        uid = ctx["user"]["id"] if ctx["user"] else None
        farm = get_farm(int(farm_id), user_id=uid) if str(farm_id).isdigit() else None
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found.")
    return farm


@app.put("/api/farms/{farm_id}")
def api_update_farm(farm_id: str, farm: FarmCreate, authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    payload = farm.model_dump()
    if ctx["mode"] == "insforge":
        try:
            updated = insforge_update_farm(ctx["token"], farm_id, payload)
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    else:
        uid = ctx["user"]["id"] if ctx["user"] else None
        payload["user_id"] = uid
        updated = update_farm(int(farm_id), payload, user_id=uid) if str(farm_id).isdigit() else None
    if not updated:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found.")
    return updated


@app.delete("/api/farms/{farm_id}")
def api_delete_farm(farm_id: str, authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] == "insforge":
        try:
            deleted = insforge_delete_farm(ctx["token"], farm_id)
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    else:
        uid = ctx["user"]["id"] if ctx["user"] else None
        deleted = delete_farm(int(farm_id), user_id=uid) if str(farm_id).isdigit() else False
    if not deleted:
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
def api_generate_advisory(
    req: AdvisoryRequest,
    authorization: Optional[str] = Header(default=None),
):
    ctx = _resolve_user_auth(authorization, required=bool(req.save_to_history))
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
        # Strip large base64 images before saving JSON to database
        clean_crop_res = {
            k: v for k, v in crop_res.items() if k not in {"original_data_uri", "gradcam_data_uri"}
        }
        assessment_payload = {
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
        }
        if ctx["mode"] == "insforge":
            try:
                saved_record = insforge_create_assessment(ctx["token"], assessment_payload)
                # Also write a concise summary row to public.crop_advisories (RLS-protected)
                actions_list = advisory_res.get("recommended_actions") or []
                top_action = (
                    actions_list[0].get("detail") or actions_list[0].get("title")
                    if actions_list
                    else advisory_res.get("possible_problem", "Follow crop advisory.")
                )
                insforge_create_crop_advisory(
                    ctx["token"],
                    {
                        "farm_name": req.farm_name or "My Farm",
                        "village": req.village or "Unknown",
                        "district": req.district or "Unknown",
                        "state": req.state or "Unknown",
                        "crop_name": assessment_payload["crop_name"],
                        "growth_stage": req.growth_stage or "vegetative",
                        "area_acres": float(req.area_acres or 1.0),
                        "predicted_disease": clean_crop_res.get("disease"),
                        "model_confidence": clean_crop_res.get("confidence"),
                        "soil_score": (soil_res or {}).get("soil_score"),
                        "risk_score": risk_res.get("risk_score"),
                        "risk_level": risk_res.get("risk_level") or "LOW",
                        "recommended_action": str(top_action)[:1800],
                    },
                )
            except (InsForgeAuthError, InsForgeDBError) as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        else:
            assessment_payload["user_id"] = ctx["user"]["id"] if ctx["user"] else None
            saved_record = create_assessment(assessment_payload)

    return {
        "risk": risk_res,
        "advisory": advisory_res,
        "soil": soil_res,
        "calendar": calendar_res,
        "saved_assessment": saved_record,
    }


# -------------------------
# Assessment History & Crop Advisories API (User-Owned via InsForge RLS)
# -------------------------

@app.get("/api/assessments")
def api_list_assessments(
    farm_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    authorization: Optional[str] = Header(default=None),
):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] == "insforge":
        try:
            items = insforge_list_assessments(ctx["token"], farm_id=farm_id, limit=limit)
            return {"count": len(items), "assessments": items, "source": "insforge"}
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    uid = ctx["user"]["id"] if ctx["user"] else None
    fid_int = int(farm_id) if (farm_id and str(farm_id).isdigit()) else None
    items = list_assessments(farm_id=fid_int, limit=limit, user_id=uid)
    return {"count": len(items), "assessments": items, "source": "sqlite"}


@app.get("/api/assessments/{assessment_id}")
def api_get_assessment(assessment_id: str, authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] == "insforge":
        try:
            record = insforge_get_assessment(ctx["token"], assessment_id)
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    else:
        uid = ctx["user"]["id"] if ctx["user"] else None
        record = get_assessment(int(assessment_id), user_id=uid) if str(assessment_id).isdigit() else None
    if not record:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")
    return record


@app.delete("/api/assessments/{assessment_id}")
def api_delete_assessment(assessment_id: str, authorization: Optional[str] = Header(default=None)):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] == "insforge":
        try:
            deleted = insforge_delete_assessment(ctx["token"], assessment_id)
        except (InsForgeAuthError, InsForgeDBError) as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    else:
        uid = ctx["user"]["id"] if ctx["user"] else None
        deleted = delete_assessment(int(assessment_id), user_id=uid) if str(assessment_id).isdigit() else False
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")
    return {"deleted": True, "id": assessment_id}


@app.get("/api/advisories")
def api_list_crop_advisories(
    limit: int = Query(default=50, ge=1, le=100),
    authorization: Optional[str] = Header(default=None),
):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] != "insforge":
        return {"count": 0, "advisories": [], "source": "sqlite"}
    try:
        items = insforge_list_crop_advisories(ctx["token"], limit=limit)
        return {"count": len(items), "advisories": items, "source": "insforge"}
    except (InsForgeAuthError, InsForgeDBError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/advisories", status_code=201)
def api_create_crop_advisory(
    req: CropAdvisoryCreate,
    authorization: Optional[str] = Header(default=None),
):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] != "insforge":
        raise HTTPException(status_code=401, detail="InsForge Auth sign-in required for cloud advisories.")
    try:
        return insforge_create_crop_advisory(ctx["token"], req.model_dump())
    except (InsForgeAuthError, InsForgeDBError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.delete("/api/advisories/{advisory_id}")
def api_delete_crop_advisory(
    advisory_id: str,
    authorization: Optional[str] = Header(default=None),
):
    ctx = _resolve_user_auth(authorization, required=True)
    if ctx["mode"] != "insforge":
        raise HTTPException(status_code=401, detail="InsForge Auth sign-in required.")
    try:
        deleted = insforge_delete_crop_advisory(ctx["token"], advisory_id)
    except (InsForgeAuthError, InsForgeDBError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Advisory {advisory_id} not found.")
    return {"deleted": True, "id": advisory_id}


# Serve the frontend directory at /app so users can open http://127.0.0.1:8000/app/
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
