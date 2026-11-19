"""
InsForge Backend Integration Service (Auth JWT Verification + RLS-Enforced Postgres CRUD).

Reads public credentials strictly from environment variables / `.env.local`
(never hardcoded in source files). Every database read and write forwards the
signed-in user's own InsForge Bearer JWT so PostgreSQL Row Level Security
(`user_id = auth.uid()`) and automatic `user_id` stamping triggers are enforced
end-to-end.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import requests

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_LOCAL_PATH = WORKSPACE_ROOT / ".env.local"


class InsForgeAuthError(Exception):
    """Raised when an InsForge Bearer token is missing, invalid, or expired."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class InsForgeDBError(Exception):
    """Raised when an InsForge Postgres PostgREST operation fails."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                values[key] = val
    except OSError:
        pass
    return values


def get_insforge_config() -> dict[str, str]:
    """Return InsForge public baseUrl and anonKey from env vars or `.env.local`."""
    file_env = _read_env_file(ENV_LOCAL_PATH)
    base_url = (
        os.environ.get("INSFORGE_URL")
        or os.environ.get("NEXT_PUBLIC_INSFORGE_URL")
        or os.environ.get("VITE_INSFORGE_URL")
        or file_env.get("INSFORGE_URL")
        or ""
    ).rstrip("/")
    anon_key = (
        os.environ.get("INSFORGE_ANON_KEY")
        or os.environ.get("NEXT_PUBLIC_INSFORGE_ANON_KEY")
        or os.environ.get("VITE_INSFORGE_ANON_KEY")
        or file_env.get("INSFORGE_ANON_KEY")
        or ""
    )
    google_client_id = (
        os.environ.get("GOOGLE_CLIENT_ID")
        or os.environ.get("NEXT_PUBLIC_GOOGLE_CLIENT_ID")
        or file_env.get("GOOGLE_CLIENT_ID")
        or ""
    ).strip()
    return {
        "baseUrl": base_url,
        "anonKey": anon_key,
        "googleClientId": google_client_id,
    }


def is_insforge_configured() -> bool:
    file_env = _read_env_file(ENV_LOCAL_PATH)
    if (
        os.environ.get("INSFORGE_USE_LOCAL_SQLITE") == "1"
        or file_env.get("INSFORGE_USE_LOCAL_SQLITE") == "1"
    ):
        return False
    cfg = get_insforge_config()
    return bool(cfg["baseUrl"] and cfg["anonKey"])


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not isinstance(authorization, str) or not authorization.strip():
        return None
    val = authorization.strip()
    if val.lower().startswith("bearer "):
        token = val[7:].strip()
        return token or None
    return val or None


def verify_insforge_token(authorization: Optional[str]) -> dict[str, Any]:
    """
    Verify an InsForge user JWT against `GET /api/auth/sessions/current`.
    Returns `{ id, email, role, access_token }` or raises InsForgeAuthError (401).
    """
    token = extract_bearer_token(authorization)
    if not token:
        raise InsForgeAuthError("Authentication required. Please sign in to access your farm data.", 401)

    cfg = get_insforge_config()
    if not cfg["baseUrl"]:
        raise InsForgeAuthError("InsForge backend URL is not configured in .env.local.", 500)

    try:
        resp = requests.get(
            f"{cfg['baseUrl']}/api/auth/sessions/current",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise InsForgeAuthError(f"Could not reach InsForge Auth service: {exc}", 503) from exc

    if resp.status_code != 200:
        raise InsForgeAuthError("Your session has expired or is invalid. Please sign in again.", 401)

    body = resp.json()
    user = body.get("user") if isinstance(body, dict) else None
    if not user or not user.get("id"):
        raise InsForgeAuthError("Invalid InsForge user session.", 401)

    return {
        "id": str(user["id"]),
        "email": user.get("email"),
        "role": user.get("role", "authenticated"),
        "access_token": token,
    }


def _db_request(
    method: str,
    table: str,
    access_token: str,
    params: Optional[dict[str, Any]] = None,
    payload: Any = None,
    prefer: Optional[str] = None,
) -> Any:
    cfg = get_insforge_config()
    url = f"{cfg['baseUrl']}/api/database/records/{table}"
    if params:
        url = f"{url}?{urlencode(params)}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    try:
        resp = requests.request(method, url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise InsForgeDBError(f"InsForge database connection error: {exc}", 503) from exc

    if resp.status_code in (401, 403):
        raise InsForgeAuthError("Access denied by Row Level Security. Please sign in.", resp.status_code)

    if not resp.ok:
        detail = resp.text
        try:
            err_json = resp.json()
            detail = err_json.get("message") or err_json.get("error") or detail
        except Exception:
            pass
        raise InsForgeDBError(f"InsForge database error ({resp.status_code}): {detail}", resp.status_code)

    if not resp.content:
        return None
    return resp.json()


# ------------------------------------------------------------------
# User-Scoped Farms CRUD (`public.farms`, RLS-protected)
# ------------------------------------------------------------------

FARM_LIST_COLUMNS = (
    "id,user_id,farm_name,village,district,state,latitude,longitude,"
    "crop_name,area_acres,plot_length_m,plot_width_m,boundary_geojson,sowing_date,created_at,updated_at"
)


def insforge_list_farms(access_token: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = _db_request(
        "GET",
        "farms",
        access_token,
        params={"select": FARM_LIST_COLUMNS, "order": "created_at.desc", "limit": limit},
    )
    return rows if isinstance(rows, list) else []


def insforge_get_farm(access_token: str, farm_id: str) -> Optional[dict[str, Any]]:
    rows = _db_request(
        "GET",
        "farms",
        access_token,
        params={"select": FARM_LIST_COLUMNS, "id": f"eq.{farm_id}", "limit": 1},
    )
    return rows[0] if isinstance(rows, list) and rows else None


def insforge_create_farm(access_token: str, farm_data: dict[str, Any]) -> dict[str, Any]:
    # Strip any caller-supplied user_id; PostgreSQL DEFAULT auth.uid() + trigger sets it automatically
    clean = {k: v for k, v in farm_data.items() if k != "user_id"}
    rows = _db_request(
        "POST",
        "farms",
        access_token,
        payload=[clean],
        prefer="return=representation",
    )
    if not isinstance(rows, list) or not rows:
        raise InsForgeDBError("Failed to create farm record in InsForge.", 500)
    return rows[0]


def insforge_update_farm(access_token: str, farm_id: str, farm_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    clean = {k: v for k, v in farm_data.items() if k not in {"id", "user_id", "created_at"}}
    rows = _db_request(
        "PATCH",
        "farms",
        access_token,
        params={"id": f"eq.{farm_id}"},
        payload=clean,
        prefer="return=representation",
    )
    return rows[0] if isinstance(rows, list) and rows else None


def insforge_delete_farm(access_token: str, farm_id: str) -> bool:
    rows = _db_request(
        "DELETE",
        "farms",
        access_token,
        params={"id": f"eq.{farm_id}"},
        prefer="return=representation",
    )
    return bool(isinstance(rows, list) and len(rows) > 0)


# ------------------------------------------------------------------
# User-Scoped Assessments CRUD (`public.assessments`, RLS-protected)
# ------------------------------------------------------------------

ASSESSMENT_LIST_COLUMNS = (
    "id,user_id,farm_id,crop_name,growth_stage,assessment_date,image_filename,"
    "predicted_disease,model_confidence,crop_status,soil_score,risk_score,risk_level"
)


def insforge_list_assessments(
    access_token: str,
    farm_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "select": ASSESSMENT_LIST_COLUMNS,
        "order": "assessment_date.desc,id.desc",
        "limit": min(max(1, limit), 100),
    }
    if farm_id:
        params["farm_id"] = f"eq.{farm_id}"
    rows = _db_request("GET", "assessments", access_token, params=params)
    return rows if isinstance(rows, list) else []


def insforge_get_assessment(access_token: str, assessment_id: str) -> Optional[dict[str, Any]]:
    rows = _db_request(
        "GET",
        "assessments",
        access_token,
        params={"id": f"eq.{assessment_id}", "limit": 1},
    )
    return rows[0] if isinstance(rows, list) and rows else None


def insforge_create_assessment(access_token: str, record: dict[str, Any]) -> dict[str, Any]:
    clean = {k: v for k, v in record.items() if k != "user_id"}
    if clean.get("soil_score") is not None:
        clean["soil_score"] = int(round(float(clean["soil_score"])))
    if clean.get("risk_score") is not None:
        clean["risk_score"] = int(round(float(clean["risk_score"])))
    rows = _db_request(
        "POST",
        "assessments",
        access_token,
        payload=[clean],
        prefer="return=representation",
    )
    if not isinstance(rows, list) or not rows:
        raise InsForgeDBError("Failed to create assessment record in InsForge.", 500)
    return rows[0]


def insforge_delete_assessment(access_token: str, assessment_id: str) -> bool:
    rows = _db_request(
        "DELETE",
        "assessments",
        access_token,
        params={"id": f"eq.{assessment_id}"},
        prefer="return=representation",
    )
    return bool(isinstance(rows, list) and len(rows) > 0)


# ------------------------------------------------------------------
# User-Scoped Crop Advisories CRUD (`public.crop_advisories`, RLS-protected)
# ------------------------------------------------------------------

ADVISORY_COLUMNS = (
    "id,user_id,farm_name,village,district,state,crop_name,growth_stage,area_acres,"
    "predicted_disease,model_confidence,soil_score,risk_score,risk_level,recommended_action,created_at"
)


def insforge_list_crop_advisories(access_token: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = _db_request(
        "GET",
        "crop_advisories",
        access_token,
        params={"select": ADVISORY_COLUMNS, "order": "created_at.desc", "limit": min(max(1, limit), 100)},
    )
    return rows if isinstance(rows, list) else []


def insforge_create_crop_advisory(access_token: str, record: dict[str, Any]) -> dict[str, Any]:
    clean = {k: v for k, v in record.items() if k != "user_id"}
    if clean.get("soil_score") is not None:
        clean["soil_score"] = int(round(float(clean["soil_score"])))
    if clean.get("risk_score") is not None:
        clean["risk_score"] = int(round(float(clean["risk_score"])))
    rows = _db_request(
        "POST",
        "crop_advisories",
        access_token,
        payload=[clean],
        prefer="return=representation",
    )
    if not isinstance(rows, list) or not rows:
        raise InsForgeDBError("Failed to create crop advisory record in InsForge.", 500)
    return rows[0]


def insforge_delete_crop_advisory(access_token: str, advisory_id: str) -> bool:
    rows = _db_request(
        "DELETE",
        "crop_advisories",
        access_token,
        params={"id": f"eq.{advisory_id}"},
        prefer="return=representation",
    )
    return bool(isinstance(rows, list) and len(rows) > 0)
