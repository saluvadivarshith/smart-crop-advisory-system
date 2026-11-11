"""
Farm location search (geocoding) and reverse geocoding.

Primary: OpenStreetMap Nominatim (free, no key; usage policy requires a
descriptive User-Agent and at most 1 request per second).
Fallback: Open-Meteo geocoding API (free, no key; coarser coverage of
villages but returns district/state).
"""

import threading
import time

import requests

NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
HEADERS = {"User-Agent": "SmartCropAdvisory/1.0 (college mini-project; educational use)"}

_lock = threading.Lock()
_last_call = [0.0]
_cache: dict = {}


class GeocodingError(Exception):
    pass


def _throttle():
    """Respect Nominatim's 1 request/second policy."""
    with _lock:
        wait = 1.0 - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()


def _village(addr):
    for key in ("village", "hamlet", "town", "suburb", "city", "municipality", "county"):
        if addr.get(key):
            return addr[key]
    return None


def _district(addr):
    for key in ("state_district", "district", "county", "city_district"):
        if addr.get(key):
            return addr[key]
    return None


def _from_nominatim(item):
    addr = item.get("address", {})
    return {
        "display_name": item.get("display_name"),
        "village": _village(addr),
        "district": _district(addr),
        "state": addr.get("state"),
        "country": addr.get("country"),
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "source": "OpenStreetMap Nominatim",
    }


def search_location(query, country_code="in", limit=6):
    query = query.strip()
    key = ("s", query.lower(), country_code)
    if key in _cache:
        return _cache[key]

    results = []
    try:
        _throttle()
        params = {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": limit}
        if country_code:
            params["countrycodes"] = country_code
        r = requests.get(NOMINATIM_SEARCH, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        results = [_from_nominatim(i) for i in r.json()]
    except (requests.RequestException, ValueError, KeyError):
        results = []

    if not results:
        try:
            params = {"name": query, "count": limit, "language": "en", "format": "json"}
            if country_code:
                params["countryCode"] = country_code.upper()
            r = requests.get(OPEN_METEO_GEOCODE, params=params, timeout=10)
            r.raise_for_status()
            for i in r.json().get("results", []) or []:
                results.append({
                    "display_name": ", ".join(x for x in [i.get("name"), i.get("admin2"), i.get("admin1"), i.get("country")] if x),
                    "village": i.get("name"),
                    "district": i.get("admin2"),
                    "state": i.get("admin1"),
                    "country": i.get("country"),
                    "latitude": i["latitude"],
                    "longitude": i["longitude"],
                    "source": "Open-Meteo Geocoding",
                })
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise GeocodingError("Location search service is not reachable. Check the internet connection.") from exc

    _cache[key] = results
    return results


def reverse_geocode(latitude, longitude):
    key = ("r", round(latitude, 4), round(longitude, 4))
    if key in _cache:
        return _cache[key]
    try:
        _throttle()
        r = requests.get(
            NOMINATIM_REVERSE,
            params={"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1, "zoom": 14},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise GeocodingError("No address found for these coordinates.")
        result = _from_nominatim(data)
        result["latitude"], result["longitude"] = latitude, longitude
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise GeocodingError("Could not look up the place name for this location.") from exc
    _cache[key] = result
    return result
