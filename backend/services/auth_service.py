"""
Farmer Authentication Service with Mandatory 2-Step Verification (OTP).

Workflow:
  1. Sign Up (Step 1):
     - Validates Full Name, Password, and Email and/or Mobile Number.
     - Checks that Email/Phone is not already registered.
     - Generates a 6-digit OTP code and sends it via:
       * Gmail (`smtplib` SSL over `smtp.gmail.com:465`) if channel == "email"
       * SMS (`Fast2SMS` / `Twilio` HTTP API) if channel == "sms"
     - Stores a pending `otp_challenges` row in SQLite (valid for 10 minutes).
     - Only creates the user account and issues a Bearer session token in Step 2
       when the 6-digit OTP is verified.
  2. Sign In (Step 1):
     - Accepts Email Address OR Mobile Number + Password.
     - Verifies the user's password hash (PBKDF2-HMAC-SHA256).
     - Generates a 6-digit OTP code for the identifier's channel ("email" if
       signed in with email, "sms" if signed in with phone) and sends it.
     - Issues the Bearer session token in Step 2 only after OTP verification.
"""

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import smtplib
from typing import Optional

import requests

from backend.database.database import get_connection
from backend.utils.validators import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERATIONS = 120_000
SESSION_DAYS = 30
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


class AuthError(Exception):
    """Raised when credentials, OTP codes, or session tokens are invalid."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


def normalize_email(raw: Optional[str]) -> Optional[str]:
    if not raw or not raw.strip():
        return None
    email = raw.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("Please enter a valid email address (for example, farmer@gmail.com).")
    return email


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    if not raw or not raw.strip():
        return None
    digits = re.sub(r"\D", "", raw.strip())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) < 10 or len(digits) > 15:
        raise ValidationError("Please enter a valid 10-digit mobile number.")
    return digits


def parse_identifier(identifier: str) -> tuple[str, str]:
    """Return ('email', normalized_email) or ('phone', normalized_phone)."""
    cleaned = (identifier or "").strip()
    if not cleaned:
        raise ValidationError("Please enter your email address or mobile number.")
    if "@" in cleaned:
        return "email", normalize_email(cleaned)
    return "phone", normalize_phone(cleaned)


def _hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    if len(password or "") < 6:
        raise ValidationError("Password must be at least 6 characters long.")
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_hex = stored_hash.split("$", 1)
        candidate = _hash_password(password, salt_hex=salt_hex)
        return hmac.compare_digest(candidate, f"{salt_hex}${expected_hex}")
    except Exception:
        return False


def _hash_otp(otp_code: str, challenge_id: str) -> str:
    return hashlib.sha256(f"{challenge_id}:{otp_code.strip()}".encode("utf-8")).hexdigest()


def _user_dict(row) -> dict:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "phone": row["phone"],
        "created_at": row["created_at"],
    }


def _create_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    conn.execute(
        "INSERT INTO auth_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at),
    )
    return token


# ------------------------------------------------------------------
# SMTP (Gmail) & SMS Gateway Settings + Delivery
# ------------------------------------------------------------------

def get_sender_settings() -> dict:
    """Load SMTP / SMS credentials from SQLite app_settings or environment variables."""
    cfg = {
        "smtp_email": os.environ.get("SMTP_EMAIL", ""),
        "smtp_app_password": os.environ.get("SMTP_APP_PASSWORD", ""),
        "fast2sms_api_key": os.environ.get("FAST2SMS_API_KEY", ""),
    }
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
            for r in rows:
                if r["value"]:
                    cfg[r["key"]] = r["value"]
    except Exception:
        pass
    return {
        "smtp_email": cfg["smtp_email"],
        "smtp_configured": bool(cfg["smtp_email"] and cfg["smtp_app_password"]),
        "sms_configured": bool(cfg["fast2sms_api_key"]),
        "_raw": cfg,
    }


def save_sender_settings(
    smtp_email: Optional[str] = None,
    smtp_app_password: Optional[str] = None,
    fast2sms_api_key: Optional[str] = None,
) -> dict:
    """Persist Gmail SMTP or Fast2SMS API credentials in SQLite app_settings."""
    with get_connection() as conn:
        if smtp_email is not None:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES ('smtp_email', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (smtp_email.strip(),),
            )
        if smtp_app_password is not None:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES ('smtp_app_password', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (smtp_app_password.strip().replace(" ", ""),),
            )
        if fast2sms_api_key is not None:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES ('fast2sms_api_key', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (fast2sms_api_key.strip(),),
            )
    info = get_sender_settings()
    return {
        "smtp_email": info["smtp_email"],
        "smtp_configured": info["smtp_configured"],
        "sms_configured": info["sms_configured"],
    }


def _read_local_env_var(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if val:
        return val
    env_path = Path(__file__).resolve().parent.parent.parent / ".env.local"
    if env_path.is_file():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
        except OSError:
            pass
    return ""


def _deliver_otp(channel: str, destination: str, otp_code: str, full_name: str) -> dict:
    """
    Deliver OTP via live Email SMTP or live SMS Gateway (Twilio / Fast2SMS).
    Never exposes a simulated OTP preview in production/browser requests;
    only permits test-mode code return when running under pytest.
    """
    settings = get_sender_settings()["_raw"]
    in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))

    if channel == "email":
        smtp_user = settings.get("smtp_email", "").strip()
        smtp_pass = settings.get("smtp_app_password", "").strip()
        if smtp_user and smtp_pass:
            try:
                msg = EmailMessage()
                msg["Subject"] = f"{otp_code} is your CropSense verification code"
                msg["From"] = f"CropSense Advisory <{smtp_user}>"
                msg["To"] = destination
                msg.set_content(
                    f"Hello {full_name},\n\n"
                    f"Your 6-digit verification code for the Smart Crop Advisory System is:\n\n"
                    f"    {otp_code}\n\n"
                    f"This code is valid for {OTP_EXPIRY_MINUTES} minutes.\n"
                    f"If you did not request this code, please ignore this email.\n"
                )
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                return {
                    "delivered_live": True,
                    "channel": "email",
                    "destination": destination,
                    "delivery_note": f"6-digit verification code sent to {destination}.",
                    "demo_otp_code": None,
                }
            except Exception as exc:
                raise AuthError(f"Could not send email OTP: {exc}", 503) from exc
        if in_pytest:
            return {
                "delivered_live": False,
                "channel": "email",
                "destination": destination,
                "delivery_note": f"Test email OTP generated for {destination}.",
                "demo_otp_code": otp_code,
            }
        raise AuthError("Email OTP is handled via Supabase Auth. Please refresh and try again.", 503)

    # 1. Live SMS via Twilio (if configured in .env.local / environment)
    twilio_sid = _read_local_env_var("TWILIO_ACCOUNT_SID")
    twilio_token = _read_local_env_var("TWILIO_AUTH_TOKEN")
    twilio_from = _read_local_env_var("TWILIO_FROM_NUMBER")
    if twilio_sid and twilio_token and twilio_from:
        try:
            resp = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                auth=(twilio_sid, twilio_token),
                data={
                    "To": f"+91{destination}",
                    "From": twilio_from,
                    "Body": f"Your CropSense verification OTP is {otp_code}. Valid for {OTP_EXPIRY_MINUTES} minutes.",
                },
                timeout=12,
            )
            if resp.ok:
                return {
                    "delivered_live": True,
                    "channel": "sms",
                    "destination": destination,
                    "delivery_note": f"6-digit SMS OTP sent to +91-{destination}.",
                    "demo_otp_code": None,
                }
            raise AuthError(f"Twilio SMS delivery failed ({resp.status_code}): {resp.text[:160]}", 502)
        except AuthError:
            raise
        except Exception as exc:
            raise AuthError(f"Could not reach Twilio SMS API: {exc}", 503) from exc

    # 2. Live SMS via Fast2SMS (if configured in .env.local / settings)
    sms_key = _read_local_env_var("FAST2SMS_API_KEY") or settings.get("fast2sms_api_key", "").strip()
    if sms_key:
        try:
            resp = requests.post(
                "https://www.fast2sms.com/dev/bulkV2",
                headers={"authorization": sms_key},
                json={
                    "route": "q",
                    "message": f"Your CropSense verification OTP is {otp_code}. Valid for {OTP_EXPIRY_MINUTES} minutes.",
                    "language": "english",
                    "numbers": destination,
                },
                timeout=12,
            )
            data = resp.json()
            if resp.ok and data.get("return"):
                return {
                    "delivered_live": True,
                    "channel": "sms",
                    "destination": destination,
                    "delivery_note": f"6-digit SMS OTP sent to +91-{destination}.",
                    "demo_otp_code": None,
                }
            raise AuthError(f"Fast2SMS delivery failed: {data.get('message') or resp.text[:160]}", 502)
        except AuthError:
            raise
        except Exception as exc:
            raise AuthError(f"Could not reach Fast2SMS API: {exc}", 503) from exc

    if in_pytest:
        return {
            "delivered_live": False,
            "channel": "sms",
            "destination": destination,
            "delivery_note": f"Test SMS OTP generated for +91-{destination}.",
            "demo_otp_code": otp_code,
        }

    raise AuthError(
        "No live SMS provider is connected yet. To receive real SMS OTPs on your mobile number, "
        "either enable Phone Auth (Twilio/Vonage) in your Supabase Dashboard, or add "
        "TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM_NUMBER (or FAST2SMS_API_KEY) in .env.local.",
        503,
    )


def _issue_otp_challenge(
    flow_type: str,
    channel: str,
    destination: str,
    payload: dict,
    full_name: str,
) -> dict:
    challenge_id = secrets.token_urlsafe(24)
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    otp_hash = _hash_otp(otp_code, challenge_id)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    with get_connection() as conn:
        conn.execute("DELETE FROM otp_challenges WHERE destination = ?", (destination,))
        conn.execute(
            """
            INSERT INTO otp_challenges
                (challenge_id, flow_type, channel, destination, otp_hash, payload_json, attempts, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (challenge_id, flow_type, channel, destination, otp_hash, json.dumps(payload), expires_at),
        )

    delivery = _deliver_otp(channel, destination, otp_code, full_name)
    return {
        "step": "verify_otp",
        "requires_otp": True,
        "challenge_id": challenge_id,
        "flow_type": flow_type,
        "channel": channel,
        "destination": destination,
        "expires_in_seconds": OTP_EXPIRY_MINUTES * 60,
        "delivered_live": delivery["delivered_live"],
        "delivery_note": delivery["delivery_note"],
        "demo_otp_code": delivery["demo_otp_code"],
    }


# ------------------------------------------------------------------
# Step 1 & Step 2 Public Auth Functions
# ------------------------------------------------------------------

def check_account_exists(identifier: str) -> dict:
    """Check if an email or phone number is already registered."""
    id_type, norm_val = parse_identifier(identifier)
    col = "email" if id_type == "email" else "phone"
    with get_connection() as conn:
        row = conn.execute(f"SELECT id, full_name FROM users WHERE {col} = ?", (norm_val,)).fetchone()
    return {
        "exists": row is not None,
        "identifier_type": id_type,
        "normalized": norm_val,
        "full_name": row["full_name"] if row else None,
    }


def signup_user(
    full_name: str,
    password: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    preferred_channel: Optional[str] = None,
    require_otp: bool = True,
) -> dict:
    """
    Step 1 of Sign Up: validate details, check duplicates, and send 6-digit OTP
    via Gmail (if email given) or SMS (if phone given).
    """
    name = (full_name or "").strip()
    if len(name) < 2:
        raise ValidationError("Please enter your full name (at least 2 characters).")

    norm_email = normalize_email(email)
    norm_phone = normalize_phone(phone)

    if not norm_email and not norm_phone:
        raise ValidationError("Please provide either an Email Address or a Mobile Number (or both) to sign up.")

    pw_hash = _hash_password(password)

    with get_connection() as conn:
        existing_row = None
        if norm_email:
            existing_row = conn.execute("SELECT * FROM users WHERE email = ?", (norm_email,)).fetchone()
        if not existing_row and norm_phone:
            existing_row = conn.execute("SELECT * FROM users WHERE phone = ?", (norm_phone,)).fetchone()

        if existing_row:
            # If the user already exists and entered the right password (or is updating their email/phone),
            # update their contact info and proceed directly to 2-Step OTP verification!
            if _verify_password(password, existing_row["password_hash"]):
                new_email = norm_email or existing_row["email"]
                new_phone = norm_phone or existing_row["phone"]
                conn.execute(
                    "UPDATE users SET full_name = ?, email = ?, phone = ? WHERE id = ?",
                    (name, new_email, new_phone, existing_row["id"]),
                )
                ch = "email" if (preferred_channel == "email" or (norm_email and preferred_channel != "sms")) else "sms"
                dest = new_email if ch == "email" and new_email else new_phone
                return _issue_otp_challenge(
                    flow_type="signin",
                    channel=ch,
                    destination=dest,
                    payload={"user_id": existing_row["id"], "full_name": name},
                    full_name=name,
                )

            matched_field = (
                norm_email
                if (norm_email and existing_row["email"] == norm_email)
                else norm_phone
            )
            raise AuthError(
                f"An account with '{matched_field}' already exists. Please Sign In with '{matched_field}' and your password.",
                status_code=409,
            )

        if not require_otp:
            cur = conn.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
                (name, norm_email, norm_phone, pw_hash),
            )
            user_id = cur.lastrowid
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            token = _create_session(conn, user_id)
            return {
                "requires_otp": False,
                "token": token,
                "user": _user_dict(row),
                "message": f"Welcome, {name}! Your farmer account has been created.",
            }

    # Choose OTP verification channel based on what the user provided
    if preferred_channel == "sms" and norm_phone:
        channel, dest = "sms", norm_phone
    elif preferred_channel == "email" and norm_email:
        channel, dest = "email", norm_email
    elif norm_email and not norm_phone:
        channel, dest = "email", norm_email
    elif norm_phone and not norm_email:
        channel, dest = "sms", norm_phone
    else:
        # Both provided: default to email if preferred_channel not specified
        channel, dest = ("email", norm_email) if preferred_channel != "sms" else ("sms", norm_phone)

    return _issue_otp_challenge(
        flow_type="signup",
        channel=channel,
        destination=dest,
        payload={
            "full_name": name,
            "email": norm_email,
            "phone": norm_phone,
            "password_hash": pw_hash,
        },
        full_name=name,
    )


def signin_user(
    identifier: str,
    password: str,
    require_otp: bool = True,
) -> dict:
    """
    Step 1 of Sign In: verify Email or Mobile Number + Password, then send a
    6-digit 2-Step Verification code via Gmail (if signed in with email) or
    SMS (if signed in with phone number).
    """
    id_type, norm_val = parse_identifier(identifier)
    col = "email" if id_type == "email" else "phone"

    with get_connection() as conn:
        row = conn.execute(f"SELECT * FROM users WHERE {col} = ?", (norm_val,)).fetchone()
        if not row:
            label = "email address" if id_type == "email" else "mobile number"
            raise AuthError(
                f"No account found with this {label} ({norm_val}). If you are a new user, please Sign Up first.",
                status_code=404,
            )
        if not _verify_password(password or "", row["password_hash"]):
            raise AuthError("Incorrect password. Please try again.", status_code=401)

        if not require_otp:
            token = _create_session(conn, row["id"])
            return {
                "requires_otp": False,
                "token": token,
                "user": _user_dict(row),
                "message": f"Welcome back, {row['full_name']}!",
            }

    channel = "email" if id_type == "email" else "sms"
    return _issue_otp_challenge(
        flow_type="signin",
        channel=channel,
        destination=norm_val,
        payload={"user_id": row["id"], "full_name": row["full_name"]},
        full_name=row["full_name"],
    )


def verify_otp_challenge(challenge_id: str, otp_code: str) -> dict:
    """
    Step 2 of Sign Up / Sign In: verify the 6-digit OTP code, finalize account
    creation (if signup), and issue the authenticated session token.
    """
    clean_code = re.sub(r"\D", "", otp_code or "")
    if len(clean_code) != 6:
        raise ValidationError("Please enter the 6-digit verification code.")

    with get_connection() as conn:
        ch = conn.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id = ?",
            ((challenge_id or "").strip(),),
        ).fetchone()
        if not ch:
            raise AuthError("Verification session not found or already used. Please request a new code.", status_code=400)

        try:
            exp = datetime.fromisoformat(ch["expires_at"])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))
                raise AuthError("This verification code has expired. Please click 'Resend Code'.", status_code=400)
        except ValueError:
            pass

        if ch["attempts"] >= MAX_OTP_ATTEMPTS:
            conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))
            raise AuthError("Too many incorrect OTP attempts. Please start again.", status_code=429)

        expected_hash = ch["otp_hash"]
        candidate_hash = _hash_otp(clean_code, ch["challenge_id"])
        if not hmac.compare_digest(candidate_hash, expected_hash):
            conn.execute(
                "UPDATE otp_challenges SET attempts = attempts + 1 WHERE challenge_id = ?",
                (ch["challenge_id"],),
            )
            remaining = max(0, MAX_OTP_ATTEMPTS - (ch["attempts"] + 1))
            raise AuthError(f"Invalid 6-digit verification code ({remaining} attempts remaining).", status_code=401)

        payload = json.loads(ch["payload_json"])
        flow_type = ch["flow_type"]
        conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))

        if flow_type == "signup":
            cur = conn.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
                (payload["full_name"], payload.get("email"), payload.get("phone"), payload["password_hash"]),
            )
            user_id = cur.lastrowid
        else:
            user_id = int(payload["user_id"])

        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        token = _create_session(conn, user_id)

    return {
        "verified": True,
        "token": token,
        "user": _user_dict(user_row),
        "message": (
            f"2-Step Verification complete! Welcome, {user_row['full_name']}."
            if flow_type == "signup"
            else f"2-Step Verification complete! Welcome back, {user_row['full_name']}."
        ),
    }


def resend_otp_challenge(challenge_id: str) -> dict:
    """Regenerate and resend a fresh 6-digit OTP code for an active challenge."""
    with get_connection() as conn:
        ch = conn.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id = ?",
            ((challenge_id or "").strip(),),
        ).fetchone()
        if not ch:
            raise AuthError("Verification session expired. Please sign in or sign up again.", status_code=400)
        payload = json.loads(ch["payload_json"])
        flow_type = ch["flow_type"]
        channel = ch["channel"]
        destination = ch["destination"]

    return _issue_otp_challenge(
        flow_type=flow_type,
        channel=channel,
        destination=destination,
        payload=payload,
        full_name=payload.get("full_name", "Farmer"),
    )


def get_user_by_token(token: Optional[str]) -> Optional[dict]:
    """Return the user associated with a valid session token, or None."""
    if not token:
        return None
    clean_tok = token.replace("Bearer ", "").strip()
    if not clean_tok:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.*, s.expires_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (clean_tok,),
        ).fetchone()
        if not row:
            return None
        try:
            exp = datetime.fromisoformat(row["expires_at"])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                conn.execute("DELETE FROM auth_sessions WHERE token = ?", (clean_tok,))
                return None
        except ValueError:
            pass
        return _user_dict(row)


def logout_token(token: Optional[str]) -> bool:
    if not token:
        return False
    clean_tok = token.replace("Bearer ", "").strip()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM auth_sessions WHERE token = ?", (clean_tok,))
        return cur.rowcount > 0


# ------------------------------------------------------------------
# Pre-Password Phone Verification Flow (New User: Phone -> OTP -> Password)
# ------------------------------------------------------------------

def start_phone_pre_password_otp(phone: str, full_name: Optional[str] = None) -> dict:
    """
    Step 1 for a phone-number user BEFORE asking for password:
    normalizes phone, checks whether user exists, and issues a 6-digit SMS OTP.
    """
    norm_phone = normalize_phone(phone)
    with get_connection() as conn:
        existing = conn.execute("SELECT id, full_name FROM users WHERE phone = ?", (norm_phone,)).fetchone()
    if existing:
        return _issue_otp_challenge(
            flow_type="phone_signin",
            channel="sms",
            destination=norm_phone,
            payload={"user_id": existing["id"], "full_name": existing["full_name"], "phone": norm_phone},
            full_name=existing["full_name"],
        )
    name = (full_name or "").strip()
    return _issue_otp_challenge(
        flow_type="phone_pre_signup",
        channel="sms",
        destination=norm_phone,
        payload={"full_name": name, "phone": norm_phone},
        full_name=name or "Farmer",
    )


def verify_phone_pre_password_otp(challenge_id: str, otp_code: str) -> dict:
    """
    Step 2 for phone flow: verifies the 6-digit SMS OTP.
    - If existing user (`phone_signin`): logs in immediately.
    - If new user (`phone_pre_signup`): returns a short-lived `verification_token`
      so Step 3 can prompt the user to set their password!
    """
    clean_code = re.sub(r"\D", "", otp_code or "")
    if len(clean_code) != 6:
        raise ValidationError("Please enter the 6-digit verification code.")

    with get_connection() as conn:
        ch = conn.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id = ?",
            ((challenge_id or "").strip(),),
        ).fetchone()
        if not ch:
            raise AuthError("Verification session not found or already used. Please request a new code.", 400)

        if ch["attempts"] >= MAX_OTP_ATTEMPTS:
            conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))
            raise AuthError("Too many incorrect attempts. Please start again.", 429)

        if not hmac.compare_digest(_hash_otp(clean_code, ch["challenge_id"]), ch["otp_hash"]):
            conn.execute(
                "UPDATE otp_challenges SET attempts = attempts + 1 WHERE challenge_id = ?",
                (ch["challenge_id"],),
            )
            remaining = max(0, MAX_OTP_ATTEMPTS - (ch["attempts"] + 1))
            raise AuthError(f"Invalid 6-digit verification code ({remaining} attempts remaining).", 401)

        payload = json.loads(ch["payload_json"])
        flow_type = ch["flow_type"]
        conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))

        if flow_type == "phone_pre_signup":
            v_token = secrets.token_urlsafe(24)
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            conn.execute(
                """
                INSERT INTO otp_challenges
                    (challenge_id, flow_type, channel, destination, otp_hash, payload_json, attempts, expires_at)
                VALUES (?, 'phone_set_password', 'sms', ?, 'verified', ?, 0, ?)
                """,
                (v_token, ch["destination"], json.dumps(payload), expires_at),
            )
            return {
                "verified": True,
                "needs_password": True,
                "verification_token": v_token,
                "phone": payload["phone"],
                "full_name": payload["full_name"],
                "message": "Mobile number verified! Now create a password for your account.",
            }

        user_id = int(payload["user_id"])
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        token = _create_session(conn, user_id)
        return {
            "verified": True,
            "needs_password": False,
            "token": token,
            "user": _user_dict(user_row),
            "message": f"Welcome back, {user_row['full_name']}!",
        }


def complete_phone_signup_with_password(
    verification_token: str,
    password: str,
    full_name: Optional[str] = None,
) -> dict:
    """Step 3 for new phone user: set password after SMS verification & issue session."""
    pw_hash = _hash_password(password)
    with get_connection() as conn:
        ch = conn.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id = ? AND flow_type = 'phone_set_password'",
            ((verification_token or "").strip(),),
        ).fetchone()
        if not ch:
            raise AuthError("Verification expired. Please verify your mobile number again.", 400)
        payload = json.loads(ch["payload_json"])
        final_name = (full_name or payload.get("full_name") or "").strip()
        if len(final_name) < 2:
            raise ValidationError("Please enter your name (at least 2 characters).")
        conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))

        cur = conn.execute(
            "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, NULL, ?, ?)",
            (final_name, payload["phone"], pw_hash),
        )
        user_id = cur.lastrowid
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        token = _create_session(conn, user_id)

    return {
        "verified": True,
        "token": token,
        "user": _user_dict(user_row),
        "message": f"Account created! Welcome, {user_row['full_name']}.",
    }


def start_pre_password_otp(identifier: str, full_name: Optional[str] = None) -> dict:
    """
    Unified Step 1 for Email OR 10-digit Mobile Number BEFORE asking for a password.
    Checks if the user exists in local SQLite and issues a 6-digit Email or SMS OTP.
    """
    raw = (identifier or "").strip()
    if "@" in raw:
        norm_val = normalize_email(raw)
        channel = "email"
        col = "email"
    else:
        norm_val = normalize_phone(raw)
        channel = "sms"
        col = "phone"

    with get_connection() as conn:
        existing = conn.execute(
            f"SELECT id, full_name FROM users WHERE {col} = ?",
            (norm_val,),
        ).fetchone()

    if existing:
        return _issue_otp_challenge(
            flow_type="local_otp_signin",
            channel=channel,
            destination=norm_val,
            payload={"user_id": existing["id"], "full_name": existing["full_name"], col: norm_val},
            full_name=existing["full_name"],
        )

    name = (full_name or "").strip()
    return _issue_otp_challenge(
        flow_type="local_pre_signup",
        channel=channel,
        destination=norm_val,
        payload={
            "full_name": name,
            "email": norm_val if channel == "email" else None,
            "phone": norm_val if channel == "sms" else None,
        },
        full_name=name or "Farmer",
    )


def verify_pre_password_otp(challenge_id: str, otp_code: str) -> dict:
    """
    Unified Step 2: verifies the 6-digit Email or SMS OTP.
    - Existing user: logs in immediately.
    - New user: returns `needs_password: True` + short-lived `verification_token` for Step 3.
    """
    clean_code = re.sub(r"\D", "", otp_code or "")
    if len(clean_code) != 6:
        raise ValidationError("Please enter the 6-digit verification code.")

    with get_connection() as conn:
        ch = conn.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id = ?",
            ((challenge_id or "").strip(),),
        ).fetchone()
        if not ch:
            raise AuthError("Verification session not found or already used. Please request a new code.", 400)

        if ch["attempts"] >= MAX_OTP_ATTEMPTS:
            conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))
            raise AuthError("Too many incorrect attempts. Please start again.", 429)

        if not hmac.compare_digest(_hash_otp(clean_code, ch["challenge_id"]), ch["otp_hash"]):
            conn.execute(
                "UPDATE otp_challenges SET attempts = attempts + 1 WHERE challenge_id = ?",
                (ch["challenge_id"],),
            )
            remaining = max(0, MAX_OTP_ATTEMPTS - (ch["attempts"] + 1))
            raise AuthError(f"Invalid 6-digit verification code ({remaining} attempts remaining).", 401)

        payload = json.loads(ch["payload_json"])
        flow_type = ch["flow_type"]
        channel = ch["channel"]
        destination = ch["destination"]
        conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))

        if flow_type in ("local_pre_signup", "phone_pre_signup"):
            v_token = secrets.token_urlsafe(24)
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            conn.execute(
                """
                INSERT INTO otp_challenges
                    (challenge_id, flow_type, channel, destination, otp_hash, payload_json, attempts, expires_at)
                VALUES (?, 'local_set_password', ?, ?, 'verified', ?, 0, ?)
                """,
                (v_token, channel, destination, json.dumps(payload), expires_at),
            )
            return {
                "verified": True,
                "needs_password": True,
                "verification_token": v_token,
                "channel": channel,
                "destination": destination,
                "phone": payload.get("phone"),
                "email": payload.get("email"),
                "full_name": payload.get("full_name", ""),
                "message": "Verified! Now create a password for your CropSense account.",
            }

        user_id = int(payload["user_id"])
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        token = _create_session(conn, user_id)
        return {
            "verified": True,
            "needs_password": False,
            "token": token,
            "user": _user_dict(user_row),
            "message": f"Welcome back, {user_row['full_name']}!",
        }


def complete_pre_password_signup(
    verification_token: str,
    password: str,
    full_name: Optional[str] = None,
) -> dict:
    """Unified Step 3 for new email or phone user: set password after OTP verification & issue session."""
    pw_hash = _hash_password(password)
    with get_connection() as conn:
        ch = conn.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id = ? AND flow_type IN ('local_set_password', 'phone_set_password')",
            ((verification_token or "").strip(),),
        ).fetchone()
        if not ch:
            raise AuthError("Verification expired. Please verify your email or mobile number again.", 400)
        payload = json.loads(ch["payload_json"])
        final_name = (full_name or payload.get("full_name") or "").strip()
        if len(final_name) < 2:
            raise ValidationError("Please enter your name (at least 2 characters).")
        conn.execute("DELETE FROM otp_challenges WHERE challenge_id = ?", (ch["challenge_id"],))

        cur = conn.execute(
            "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
            (final_name, payload.get("email"), payload.get("phone"), pw_hash),
        )
        user_id = cur.lastrowid
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        token = _create_session(conn, user_id)

    return {
        "verified": True,
        "token": token,
        "user": _user_dict(user_row),
        "message": f"Account created! Welcome, {user_row['full_name']}.",
    }


def signin_with_google_id_token(credential: str, expected_client_id: Optional[str] = None) -> dict:
    """
    Verify a Google Identity Services ID token via Google's official tokeninfo API
    and sign in (or create) the verified user in CropSense.
    """
    raw_cred = (credential or "").strip()
    if not raw_cred:
        raise ValidationError("Google ID token is required.")

    try:
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": raw_cred},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Could not reach Google Auth API: {exc}", 503) from exc

    if resp.status_code != 200:
        raise AuthError("Invalid or expired Google Sign-In token. Please try again.", 401)

    info = resp.json()
    if expected_client_id and info.get("aud") != expected_client_id:
        raise AuthError("Google token audience mismatch.", 401)

    email = (info.get("email") or "").strip().lower()
    email_verified = str(info.get("email_verified", "")).lower() == "true"
    if not email or not email_verified:
        raise AuthError("Google account email is not verified.", 401)

    full_name = (info.get("name") or email.split("@")[0]).strip()
    with get_connection() as conn:
        existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            user_row = existing
            user_id = existing["id"]
        else:
            # Random unusable password hash for Google-authenticated accounts
            pw_hash = _hash_password(secrets.token_urlsafe(24))
            cur = conn.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?, ?, NULL, ?)",
                (full_name, email, pw_hash),
            )
            user_id = cur.lastrowid
            user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        token = _create_session(conn, user_id)

    return {
        "verified": True,
        "provider": "google",
        "token": token,
        "user": _user_dict(user_row),
        "message": f"Signed in with Google! Welcome, {user_row['full_name']}.",
    }
