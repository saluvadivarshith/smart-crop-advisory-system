"""
Farm-specific weather from the free Open-Meteo API (no API key).

Besides current conditions and a 7-day forecast, this module derives
farmer-oriented indicators:

  * humid_hours      – hours per day with relative humidity >= 90 %.
                       A widely used proxy for leaf wetness (disease risk).
  * spray_windows    – daytime periods in the next 48 h that are suitable for
                       spraying / foliar work (light wind, no rain expected,
                       not too hot). General good-practice guidance only.
  * irrigation       – compares forecast rain with FAO-56 reference
                       evapotranspiration (ET0) over the next 3 days.
  * rain_alerts      – days reaching IMD "heavy rain" category (>= 64.5 mm).

All values are MODEL FORECASTS for the farm's grid cell, not measurements
from the farmer's field.
"""

import time
from collections import defaultdict
from datetime import datetime

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 600
_cache: dict = {}


class WeatherServiceError(Exception):
    """Raised when weather data cannot be fetched or understood."""


# WMO weather interpretation codes (Open-Meteo documentation).
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog with frost",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light rain showers", 81: "Rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}

# Spray-window thresholds (general good agricultural practice).
SPRAY_WIND_MIN, SPRAY_WIND_MAX = 2, 15      # km/h – too calm risks drift by inversion, too windy drifts
SPRAY_TEMP_MAX = 30                          # °C – hotter air increases evaporation and volatility
SPRAY_RAIN_PROB_MAX = 30                     # % – no rain expected...
SPRAY_RAINFREE_HOURS = 4                     # ...for this many hours after spraying
HEAVY_RAIN_MM = 64.5                         # IMD heavy-rainfall threshold (mm/day)


def describe_code(code):
    return WEATHER_CODES.get(code, "Unknown")


def _fetch(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code,is_day",
        "hourly": ("temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,"
                   "wind_speed_10m,soil_moisture_0_to_1cm,soil_moisture_3_to_9cm"),
        "daily": ("weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                  "precipitation_probability_max,et0_fao_evapotranspiration,wind_speed_10m_max"),
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise WeatherServiceError("The weather service took too long to respond. Please try again.") from exc
    except requests.RequestException as exc:
        raise WeatherServiceError("Could not reach the weather service. Check the internet connection.") from exc
    except ValueError as exc:
        raise WeatherServiceError("The weather service returned an unreadable response.") from exc


def _hourly_records(hourly):
    keys = ["temperature_2m", "relative_humidity_2m", "precipitation_probability",
            "precipitation", "wind_speed_10m", "soil_moisture_0_to_1cm", "soil_moisture_3_to_9cm"]
    records = []
    for i, t in enumerate(hourly.get("time", [])):
        rec = {"time": t}
        for k in keys:
            values = hourly.get(k) or []
            rec[k] = values[i] if i < len(values) else None
        records.append(rec)
    return records


def _spray_windows(records):
    """Find daytime periods (>= 2 h) suitable for spraying in the given hours."""
    suitable = []
    for i, r in enumerate(records):
        hour = int(r["time"][11:13])
        if not 6 <= hour <= 18:
            suitable.append(False)
            continue
        wind, temp, prob = r["wind_speed_10m"], r["temperature_2m"], r["precipitation_probability"]
        if None in (wind, temp):
            suitable.append(False)
            continue
        ahead = records[i:i + SPRAY_RAINFREE_HOURS]
        rain_ahead = sum((a["precipitation"] or 0) for a in ahead)
        prob_ahead = max(((a["precipitation_probability"] or 0) for a in ahead), default=0)
        ok = (SPRAY_WIND_MIN <= wind <= SPRAY_WIND_MAX and temp <= SPRAY_TEMP_MAX
              and (prob or 0) <= SPRAY_RAIN_PROB_MAX and prob_ahead <= SPRAY_RAIN_PROB_MAX
              and rain_ahead < 0.2)
        suitable.append(ok)

    windows, start = [], None
    for i, ok in enumerate(suitable + [False]):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            if i - start >= 2:
                block = records[start:i]
                windows.append({
                    "start": block[0]["time"],
                    "end": records[i - 1]["time"][:11] + f"{int(records[i - 1]['time'][11:13]) + 1:02d}:00",
                    "hours": i - start,
                    "max_wind_kmh": round(max(b["wind_speed_10m"] for b in block), 1),
                    "max_temp_c": round(max(b["temperature_2m"] for b in block), 1),
                })
            start = None
    return windows


def _irrigation_hint(daily):
    rain = sum((d["precipitation_sum"] or 0) for d in daily[:3])
    et0 = sum((d["et0_mm"] or 0) for d in daily[:3])
    deficit = round(max(et0 - rain, 0), 1)
    if et0 <= 0:
        advice = "Not enough data to estimate crop water need."
        status = "unknown"
    elif rain >= et0:
        status = "rain_sufficient"
        advice = ("Forecast rain over the next 3 days is about equal to or more than the expected water loss. "
                  "You may be able to postpone irrigation. Check soil moisture by hand before irrigating.")
    elif rain >= 10:
        status = "partial"
        advice = ("Some rain is expected but it may not fully cover crop water need. "
                  "Check soil moisture and irrigate lightly if the soil is dry at root depth.")
    else:
        status = "irrigation_likely"
        advice = ("Little rain is expected. Plan irrigation according to your crop stage and soil moisture.")
    return {
        "status": status,
        "rain_next_3_days_mm": round(rain, 1),
        "et0_next_3_days_mm": round(et0, 1),
        "water_deficit_mm": deficit,
        "advice": advice,
        "note": "ET0 is reference evapotranspiration (FAO-56) for a standard grass surface. "
                "Actual crop water use depends on crop type and growth stage.",
    }


def get_weather(latitude, longitude):
    """Return current weather, a 7-day forecast and derived farm indicators."""
    cache_key = (round(latitude, 2), round(longitude, 2))
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    raw = _fetch(latitude, longitude)
    try:
        current = raw["current"]
        daily_raw = raw["daily"]
        records = _hourly_records(raw.get("hourly", {}))
    except (KeyError, TypeError) as exc:
        raise WeatherServiceError("Weather data was incomplete.") from exc

    # Start hourly records from the current hour.
    now_hour = current["time"][:13]
    start_idx = next((i for i, r in enumerate(records) if r["time"][:13] >= now_hour), 0)
    upcoming = records[start_idx:]

    humid_by_day = defaultdict(int)
    for r in records:
        if (r["relative_humidity_2m"] or 0) >= 90:
            humid_by_day[r["time"][:10]] += 1

    daily = []
    for i, date in enumerate(daily_raw.get("time", [])):
        def val(key):
            arr = daily_raw.get(key) or []
            return arr[i] if i < len(arr) else None
        code = val("weather_code")
        daily.append({
            "date": date,
            "weather_code": code,
            "description": describe_code(code),
            "temp_max": val("temperature_2m_max"),
            "temp_min": val("temperature_2m_min"),
            "precipitation_sum": val("precipitation_sum"),
            "precipitation_probability_max": val("precipitation_probability_max"),
            "et0_mm": val("et0_fao_evapotranspiration"),
            "wind_speed_max": val("wind_speed_10m_max"),
            "humid_hours": humid_by_day.get(date, 0),
        })

    now = upcoming[0] if upcoming else {}
    rain_alerts = [
        {"date": d["date"], "precipitation_sum": d["precipitation_sum"]}
        for d in daily if (d["precipitation_sum"] or 0) >= HEAVY_RAIN_MM
    ]

    result = {
        "location": {
            "latitude": raw.get("latitude"), "longitude": raw.get("longitude"),
            "elevation_m": raw.get("elevation"), "timezone": raw.get("timezone"),
        },
        "current": {
            "time": current.get("time"),
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "description": describe_code(current.get("weather_code")),
            "is_day": current.get("is_day"),
            "soil_moisture_0_1cm": now.get("soil_moisture_0_to_1cm"),
            "soil_moisture_3_9cm": now.get("soil_moisture_3_to_9cm"),
        },
        "daily": daily,
        "hourly_next_72h": [
            {k: r[k] for k in ("time", "temperature_2m", "relative_humidity_2m",
                               "precipitation_probability", "precipitation", "wind_speed_10m")}
            for r in upcoming[:72]
        ],
        "spray_windows": _spray_windows(upcoming[:48]),
        "irrigation": _irrigation_hint(daily),
        "rain_alerts": rain_alerts,
        "units": {
            "temperature": "°C", "humidity": "%", "wind_speed": "km/h",
            "precipitation": "mm", "et0": "mm", "soil_moisture": "m³/m³",
        },
        "source": "Open-Meteo forecast model (open-meteo.com)",
        "note": "Forecast values are model estimates for your farm area, not measurements from your field.",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        # Backward-compatible flat fields used by the original frontend.
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "rain_probability": daily[0]["precipitation_probability_max"] if daily else None,
    }
    _cache[cache_key] = (time.time(), result)
    return result
