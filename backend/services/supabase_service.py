"""
Supabase Authentication Verification Service.

Reads SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY strictly from environment
variables or `.env.local` (never hardcoded in source files). Verifies user
Bearer JWTs against Supabase Auth (`GET /auth/v1/user`) and maps each verified
Supabase user to a local user record so all localhost farms and assessments
remain strictly isolated per signed-in user.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Optional

import requests

from backend.database.database import get_connection
from backend.services.auth_service import _hash_password, _user_dict

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_LOCAL_PATH = WORKSPACE_ROOT / ".env.local"


class SupabaseAuthError(Exception):
    """Raised when a Supabase Bearer token is missing, invalid, or expired."""

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


def get_supabase_config() -> dict[str, str]:
    """Return public Supabase project URL and publishable key from env or `.env.local`."""
    file_env = _read_env_file(ENV_LOCAL_PATH)
    url = (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        or os.environ.get("VITE_SUPABASE_URL")
        or file_env.get("SUPABASE_URL")
        or ""
    ).rstrip("/")
    publishable_key = (
        os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
        or file_env.get("SUPABASE_PUBLISHABLE_KEY")
        or ""
    ).strip()
    return {
        "url": url,
        "publishableKey": publishable_key,
    }


def is_supabase_configured() -> bool:
    cfg = get_supabase_config()
    return bool(cfg["url"] and cfg["publishableKey"])


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not isinstance(authorization, str) or not authorization.strip():
        return None
    val = authorization.strip()
    if val.lower().startswith("bearer "):
        token = val[7:].strip()
        return token or None
    return val or None


def verify_supabase_token(authorization: Optional[str]) -> dict[str, Any]:
    """
    Verify a Supabase Auth JWT against `GET {SUPABASE_URL}/auth/v1/user`
    and sync/map the verified user into local SQLite for per-user data scoping.
    """
    token = extract_bearer_token(authorization)
    if not token:
        raise SupabaseAuthError("Authentication required. Please sign in.", 401)

    cfg = get_supabase_config()
    if not cfg["url"] or not cfg["publishableKey"]:
        raise SupabaseAuthError("Supabase Auth is not configured in .env.local.", 500)

    try:
        resp = requests.get(
            f"{cfg['url']}/auth/v1/user",
            headers={
                "apikey": cfg["publishableKey"],
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise SupabaseAuthError(f"Could not reach Supabase Auth: {exc}", 503) from exc

    if resp.status_code != 200:
        raise SupabaseAuthError("Your Supabase session has expired or is invalid. Please log in again.", 401)

    sb_user = resp.json()
    sb_id = sb_user.get("id")
    if not sb_id:
        raise SupabaseAuthError("Invalid Supabase user payload.", 401)

    email = (sb_user.get("email") or "").strip().lower() or None
    meta = sb_user.get("user_metadata") or {}
    full_name = (
        meta.get("full_name")
        or meta.get("name")
        or (email.split("@")[0] if email else "Farmer")
    ).strip()

    # Map verified Supabase user to a stable local SQLite user row for farm/assessment ownership
    with get_connection() as conn:
        row = None
        if email:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            pw_hash = _hash_password(secrets.token_urlsafe(24))
            cur = conn.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, ?, NULL, ?)",
                (full_name, email or f"{sb_id}@supabase.local", pw_hash),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        elif full_name and row["full_name"] != full_name and full_name != (email or "").split("@")[0]:
            conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, row["id"]))
            row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

        local_user = _user_dict(row)
        local_user["supabase_id"] = str(sb_id)
        local_user["access_token"] = token
        return local_user
