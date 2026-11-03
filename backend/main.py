from fastapi import FastAPI, UploadFile, File 
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.soil_service import analyze_soil
from backend.services.weather_service import get_weather

app = FastAPI(  
    title="Smart Crop Advisory API",
    version="1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Home
# -------------------------

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Smart Crop Advisory Backend is running"
    }


# -------------------------
# Health Check
# -------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# -------------------------
# Soil Data Structure
# -------------------------

class SoilData(BaseModel):

    N: float
    P: float
    K: float
    S: float

    Zn: float
    Fe: float
    Cu: float
    Mn: float
    B: float

    pH: float
    EC: float
    OC: float


# -------------------------
# Soil Analysis API
# -------------------------

@app.post("/api/soil/analyze")
def soil_analysis(data: SoilData):

    result = analyze_soil(
        data.model_dump()
    )

    return result
# -------------------------
# Weather API
# -------------------------

@app.get("/api/weather")
def weather(
    latitude: float,
    longitude: float
):

    result = get_weather(
        latitude,
        longitude
    )

    return result
@app.post("/api/crop/analyze")
async def crop_analysis(image: UploadFile = File(...)):

    return {
        "filename": image.filename,
        "crop": "Tomato",
        "disease": "Early Blight",
        "confidence": 0.91,
        "status": "test_only",
        "message": "Image received successfully. ML model not connected yet."
    }