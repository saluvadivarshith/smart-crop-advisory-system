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
CREATE TABLE IF NOT EXISTS farms (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
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
            ("plot_length_m", "REAL"),
            ("plot_width_m", "REAL"),
            ("boundary_geojson", "TEXT"),
        ]
        for col_name, col_type in migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE farms ADD COLUMN {col_name} {col_type}")


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
