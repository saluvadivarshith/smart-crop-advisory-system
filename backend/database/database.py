"""
SQLite connection handling.

We deliberately use Python's built-in ``sqlite3`` module instead of an ORM
so that the data layer stays small and easy to explain.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# The database path can be overridden (used by the automated tests).
DB_PATH = Path(os.environ.get("CROP_ADVISORY_DB", BACKEND_DIR / "data" / "crop_advisory.db"))


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name         TEXT    NOT NULL,
    email             TEXT    UNIQUE,
    phone             TEXT    UNIQUE,
    password_hash     TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token             TEXT    PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at        TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_challenges (
    challenge_id      TEXT    PRIMARY KEY,
    flow_type         TEXT    NOT NULL,
    channel           TEXT    NOT NULL,
    destination       TEXT    NOT NULL,
    otp_hash          TEXT    NOT NULL,
    payload_json      TEXT    NOT NULL,
    attempts          INTEGER NOT NULL DEFAULT 0,
    expires_at        TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key               TEXT    PRIMARY KEY,
    value             TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS farms (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER REFERENCES users(id) ON DELETE CASCADE,
    farm_name         TEXT    NOT NULL,
    village           TEXT,
    district          TEXT,
    state             TEXT,
    latitude          REAL    NOT NULL,
    longitude         REAL    NOT NULL,
    crop_name         TEXT,
    area_acres        REAL,
    plot_length_m     REAL,
    plot_width_m      REAL,
    boundary_geojson  TEXT,
    sowing_date       TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assessments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER REFERENCES users(id) ON DELETE CASCADE,
    farm_id           INTEGER REFERENCES farms(id) ON DELETE SET NULL,
    crop_name         TEXT    NOT NULL,
    growth_stage      TEXT,
    assessment_date   TEXT    NOT NULL DEFAULT (datetime('now')),
    image_filename    TEXT,
    predicted_disease TEXT,
    model_confidence  REAL,
    crop_status       TEXT,
    soil_score        REAL,
    soil_data         TEXT,
    weather_data      TEXT,
    risk_score        REAL,
    risk_level        TEXT,
    advisory          TEXT,
    details           TEXT
);

CREATE INDEX IF NOT EXISTS idx_assessments_farm ON assessments(farm_id, assessment_date);
"""


def get_db_path() -> Path:
    return Path(os.environ.get("CROP_ADVISORY_DB", DB_PATH))


def init_db() -> None:
    """Create the database file and tables if they do not exist, and migrate new columns."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        existing_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(farms)").fetchall()
        }
        migrations = [
            ("user_id", "INTEGER"),
            ("plot_length_m", "REAL"),
            ("plot_width_m", "REAL"),
            ("boundary_geojson", "TEXT"),
            ("sowing_date", "TEXT"),
        ]
        for col_name, col_type in migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE farms ADD COLUMN {col_name} {col_type}")

        assess_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(assessments)").fetchall()
        }
        if "user_id" not in assess_cols:
            conn.execute("ALTER TABLE assessments ADD COLUMN user_id INTEGER")


@contextmanager
def get_connection():
    """Yield a connection that commits on success and always closes."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
