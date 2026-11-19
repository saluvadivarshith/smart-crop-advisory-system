"""
Clerk Authentication Verification Service for FastAPI.

Reads CLERK_PUBLISHABLE_KEY (or NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY / VITE_CLERK_PUBLISHABLE_KEY)
and CLERK_SECRET_KEY strictly from environment variables / `.env.local` (never hardcoded,
and CLERK_SECRET_KEY is NEVER exposed to client code).

Verifies Clerk session JWTs cryptographically using Clerk's JWKS endpoint (RS256)
and maps each verified Clerk user (`sub`) to a local user row in SQLite so all
farms and assessments are strictly scoped to the signed-in user.
"""

from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path
from typing import Any, Optional

import jwt
from jwt import PyJWKClient
import requests

from backend.database.database import get_connection
from backend.services.auth_service import _hash_password, _user_dict

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_LOCAL_PATH = WORKSPACE_ROOT / ".env.local"
ENV_FALLBACK_PATH = WORKSPACE_ROOT / ".env"

_jwks_clients: dict[str, PyJWKClient] = {}
_clerk_user_cache: dict[str, dict[str, Any]] = {}


class ClerkAuthError(Exception):
    """Raised when a Clerk session JWT is missing, invalid, or expired."""

    def __init__(self, message: str, status_code: int = 401):
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


def _decode_frontend_api(publishable_key: str) -> str:
    """Decode Clerk's Frontend API hostname from `pk_test_<b64>$` or `pk_live_<b64>$`."""
    if not publishable_key or "_" not in publishable_key:
        return ""
    parts = publishable_key.split("_", 2)
    if len(parts) < 3:
        return ""
    b64_part = parts[2]
    padded = b64_part + "=" * ((4 - len(b64_part) % 4) % 4)
    try:
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore").rstrip("$").strip()
        if decoded and "." in decoded:
            return f"https://{decoded}"
    except Exception:
        pass
    return ""


def get_clerk_public_config() -> dict[str, str]:
    """Return ONLY safe public Clerk config (publishableKey + frontendApi). Never returns secret key."""
    env_vals = {**_read_env_file(ENV_FALLBACK_PATH), **_read_env_file(ENV_LOCAL_PATH)}
    pub_key = (
        os.environ.get("CLERK_PUBLISHABLE_KEY")
        or os.environ.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
        or os.environ.get("VITE_CLERK_PUBLISHABLE_KEY")
        or env_vals.get("CLERK_PUBLISHABLE_KEY")
        or env_vals.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
        or env_vals.get("VITE_CLERK_PUBLISHABLE_KEY")
        or ""
    ).strip()
    return {
        "publishableKey": pub_key,
        "frontendApi": _decode_frontend_api(pub_key),
    }


def _get_clerk_secret_key() -> str:
    env_vals = {**_read_env_file(ENV_FALLBACK_PATH), **_read_env_file(ENV_LOCAL_PATH)}
    return (
        os.environ.get("CLERK_SECRET_KEY")
        or env_vals.get("CLERK_SECRET_KEY")
        or ""
    ).strip()


def is_clerk_configured() -> bool:
    cfg = get_clerk_public_config()
    return bool(cfg["publishableKey"] and cfg["frontendApi"])


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not isinstance(authorization, str) or not authorization.strip():
        return None
    val = authorization.strip()
    if val.lower().startswith("bearer "):
        token = val[7:].strip()
        return token or None
    return val or None


def _get_jwks_client(frontend_api: str) -> PyJWKClient:
    jwks_url = f"{frontend_api.rstrip('/')}/.well-known/jwks.json"
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        _jwks_clients[jwks_url] = client
    return client


def _fetch_clerk_user_profile(clerk_user_id: str) -> dict[str, Optional[str]]:
    if clerk_user_id in _clerk_user_cache:
        return _clerk_user_cache[clerk_user_id]

    secret = _get_clerk_secret_key()
    profile: dict[str, Optional[str]] = {"email": None, "phone": None, "full_name": None}
    if not secret:
        return profile

    try:
        resp = requests.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=8,
        )
        if resp.ok:
            data = resp.json()
            emails = data.get("email_addresses") or []
            primary_email_id = data.get("primary_email_address_id")
            email = None
            for e in emails:
                if e.get("id") == primary_email_id:
                    email = e.get("email_address")
                    break
            if not email and emails:
                email = emails[0].get("email_address")

            phones = data.get("phone_numbers") or []
            phone = phones[0].get("phone_number") if phones else None

            first = (data.get("first_name") or "").strip()
            last = (data.get("last_name") or "").strip()
            full_name = f"{first} {last}".strip() or (data.get("username") or "").strip() or None

            profile = {
                "email": email.strip().lower() if email else None,
                "phone": phone,
                "full_name": full_name,
            }
            _clerk_user_cache[clerk_user_id] = profile
    except requests.RequestException:
        pass
    return profile


def verify_clerk_token(authorization: Optional[str]) -> dict[str, Any]:
    """
    Verify a Clerk session JWT using Clerk's RS256 JWKS endpoint and map the
    verified Clerk user (`sub`) to a local user row in SQLite.
    """
    token = extract_bearer_token(authorization)
    if not token:
        raise ClerkAuthError("Authentication required. Please sign in.", 401)

    cfg = get_clerk_public_config()
    if not cfg["frontendApi"]:
        raise ClerkAuthError("Clerk publishable key is not configured.", 500)

    try:
        jwks_client = _get_jwks_client(cfg["frontendApi"])
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=cfg["frontendApi"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ClerkAuthError("Your session has expired. Please sign in again.", 401) from exc
    except Exception as exc:
        raise ClerkAuthError(f"Invalid Clerk session token: {exc}", 401) from exc

    clerk_user_id = str(claims.get("sub") or "").strip()
    if not clerk_user_id:
        raise ClerkAuthError("Clerk token missing subject (sub).", 401)

    profile = _fetch_clerk_user_profile(clerk_user_id)
    email = profile.get("email") or f"{clerk_user_id}@clerk.local"
    full_name = profile.get("full_name") or (email.split("@")[0] if "@" in email else "Farmer")
    phone = profile.get("phone")

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            pw_hash = _hash_password(secrets.token_urlsafe(24))
            cur = conn.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
                (full_name, email, phone, pw_hash),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        elif full_name and row["full_name"] != full_name and full_name != email.split("@")[0]:
            conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, row["id"]))
            row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

        local_user = _user_dict(row)
        local_user["clerk_id"] = clerk_user_id
        local_user["access_token"] = token
        return local_user
