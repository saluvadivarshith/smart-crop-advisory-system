"""
Pydantic request and response models for the Smart Crop Advisory API.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class SoilData(BaseModel):
    """
    Soil Health Card parameters.
    All 12 parameters are optional so that a farmer with a partial card
    (e.g. only N, P, K, pH, OC) can still get a meaningful soil analysis.
    """
    crop: Optional[str] = Field(default=None, description="Crop name for crop-specific pH/salinity rules")
    N: Optional[float] = Field(default=None, ge=0, le=5000, description="Available Nitrogen (kg/ha)")
    P: Optional[float] = Field(default=None, ge=0, le=1000, description="Available Phosphorus (kg/ha)")
    K: Optional[float] = Field(default=None, ge=0, le=5000, description="Available Potassium (kg/ha)")
    S: Optional[float] = Field(default=None, ge=0, le=1000, description="Available Sulphur (mg/kg)")
    Zn: Optional[float] = Field(default=None, ge=0, le=200, description="Available Zinc (mg/kg)")
    Fe: Optional[float] = Field(default=None, ge=0, le=1000, description="Available Iron (mg/kg)")
    Cu: Optional[float] = Field(default=None, ge=0, le=200, description="Available Copper (mg/kg)")
    Mn: Optional[float] = Field(default=None, ge=0, le=1000, description="Available Manganese (mg/kg)")
    B: Optional[float] = Field(default=None, ge=0, le=200, description="Available Boron (mg/kg)")
    pH: Optional[float] = Field(default=None, ge=2.0, le=12.0, description="Soil pH (2.0 – 12.0)")
    EC: Optional[float] = Field(default=None, ge=0, le=50.0, description="Electrical Conductivity (dS/m)")
    OC: Optional[float] = Field(default=None, ge=0, le=20.0, description="Organic Carbon (%)")


class FarmCreate(BaseModel):
    farm_name: str = Field(..., min_length=1, max_length=120, description="Farm name or identifier")
    village: Optional[str] = Field(default=None, max_length=120)
    district: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    crop_name: Optional[str] = Field(default="Tomato", max_length=80)
    area_acres: Optional[float] = Field(default=None, ge=0, le=10000)
    plot_length_m: Optional[float] = Field(default=None, ge=0, le=50000, description="Plot length in meters")
    plot_width_m: Optional[float] = Field(default=None, ge=0, le=50000, description="Plot width in meters")
    boundary_geojson: Optional[list[list[float]]] = Field(
        default=None,
        description="List of [latitude, longitude] polygon vertices drawn on map",
    )
    sowing_date: Optional[str] = Field(default=None, max_length=32)

    @field_validator("farm_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Farm name cannot be blank.")
        return cleaned


class AdvisoryRequest(BaseModel):
    """
    Request payload for the integrated risk & advisory engine.
    Accepts pre-computed results or raw soil/coordinates, and optionally saves to SQLite.
    """
    farm_id: Optional[int] = None
    crop_name: str = Field(default="Tomato", min_length=1, max_length=80)
    growth_stage: Optional[str] = Field(default="vegetative", max_length=40)
    sowing_date: Optional[str] = Field(default=None, max_length=32)
    area_acres: Optional[float] = Field(default=None, ge=0, le=10000)
    crop_result: Optional[dict[str, Any]] = None
    soil_data: Optional[SoilData] = None
    soil_result: Optional[dict[str, Any]] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    weather_result: Optional[dict[str, Any]] = None
    save_to_history: bool = True


class SampleLeafRequest(BaseModel):
    class_folder: str = Field(..., min_length=2, max_length=150)


class SoilTextParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class CalendarRequest(BaseModel):
    crop_name: str = Field(default="Tomato", max_length=80)
    sowing_date: Optional[str] = Field(default=None, max_length=32)
    growth_stage: Optional[str] = Field(default="vegetative", max_length=40)
    area_acres: Optional[float] = Field(default=1.0, ge=0, le=10000)
    weather_result: Optional[dict[str, Any]] = None


class NewFarmPlanRequest(BaseModel):
    season: Optional[str] = Field(default=None, description="kharif, rabi, zaid, or auto")
    water_source: str = Field(default="limited", description="rain_only, limited, or assured")
    budget: str = Field(default="low", description="low, medium, or high")
    labour: str = Field(default="family", description="self, family, or hired")
    area_acres: Optional[float] = Field(default=1.0, ge=0, le=10000)
    soil_ph: Optional[float] = Field(default=None, ge=2.0, le=12.0)
    soil_ec: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    soil_n: Optional[float] = Field(default=None, ge=0.0, le=5000.0)
    selected_crop: Optional[str] = Field(default=None, max_length=80)


class InputsRecommendRequest(BaseModel):
    crop_name: str = Field(default="Tomato", max_length=80)
    area_acres: Optional[float] = Field(default=1.0, ge=0, le=10000)
    soil_values: Optional[dict[str, Any]] = None
    crop_result: Optional[dict[str, Any]] = None
    shc_npk: Optional[dict[str, Any]] = None
    prices: Optional[dict[str, Any]] = None


class AuthSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(..., min_length=6, max_length=128)
    preferred_channel: Optional[str] = Field(default=None, description="email or sms")


class AuthSigninRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=150, description="Email address or mobile phone number")
    password: str = Field(..., min_length=1, max_length=128)


class AuthCheckRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=150, description="Email address or mobile phone number")


class AuthVerifyOtpRequest(BaseModel):
    challenge_id: str = Field(..., min_length=6, max_length=120)
    otp_code: str = Field(..., min_length=4, max_length=12)


class AuthResendOtpRequest(BaseModel):
    challenge_id: str = Field(..., min_length=6, max_length=120)


class AuthSenderConfigRequest(BaseModel):
    smtp_email: Optional[str] = Field(default=None, max_length=150)
    smtp_app_password: Optional[str] = Field(default=None, max_length=150)
    fast2sms_api_key: Optional[str] = Field(default=None, max_length=250)
