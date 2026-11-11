"""
Data-access functions (create / read / update / delete) for farms and
assessments. JSON columns are stored as text and decoded on read.
"""

import json
from typing import Any, Optional

from backend.database.database import get_connection

FARM_FIELDS = [
    "farm_name", "village", "district", "state",
    "latitude", "longitude", "crop_name", "area_acres",
    "plot_length_m", "plot_width_m", "boundary_geojson", "sowing_date",
]

JSON_COLUMNS = ["soil_data", "weather_data", "advisory", "details", "boundary_geojson"]


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    data = dict(row)
    for col in JSON_COLUMNS:
        if col in data and data[col]:
            try:
                data[col] = json.loads(data[col])
            except (TypeError, ValueError):
                pass
    return data


# ---------------------------------------------------------------- farms

def _prepare_farm_values(farm: dict) -> list:
    data = dict(farm)
    if data.get("boundary_geojson") is not None and not isinstance(data["boundary_geojson"], str):
        data["boundary_geojson"] = json.dumps(data["boundary_geojson"])
    return [data.get(f) for f in FARM_FIELDS]


def create_farm(farm: dict) -> dict:
    values = _prepare_farm_values(farm)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO farms ({', '.join(FARM_FIELDS)}) "
            f"VALUES ({', '.join('?' for _ in FARM_FIELDS)})",
            values,
        )
        farm_id = cur.lastrowid
    return get_farm(farm_id)


def list_farms() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM farms ORDER BY id DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_farm(farm_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
    return _row_to_dict(row)


def update_farm(farm_id: int, farm: dict) -> Optional[dict]:
    assignments = ", ".join(f"{f} = ?" for f in FARM_FIELDS)
    values = _prepare_farm_values(farm) + [farm_id]
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE farms SET {assignments} WHERE id = ?", values)
        if cur.rowcount == 0:
            return None
    return get_farm(farm_id)


def delete_farm(farm_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM farms WHERE id = ?", (farm_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------- assessments

def create_assessment(record: dict[str, Any]) -> dict:
    record = dict(record)
    for col in JSON_COLUMNS:
        if col in record and record[col] is not None and not isinstance(record[col], str):
            record[col] = json.dumps(record[col], ensure_ascii=False)
    columns = list(record.keys())
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO assessments ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            [record[c] for c in columns],
        )
        new_id = cur.lastrowid
    return get_assessment(new_id)


def get_assessment(assessment_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
        ).fetchone()
    return _row_to_dict(row)


def list_assessments(farm_id: Optional[int] = None, limit: int = 50) -> list[dict]:
    """Return a lightweight list (without the large JSON blobs)."""
    sql = (
        "SELECT id, farm_id, crop_name, growth_stage, assessment_date, image_filename, "
        "predicted_disease, model_confidence, crop_status, soil_score, risk_score, risk_level "
        "FROM assessments"
    )
    params: list[Any] = []
    if farm_id is not None:
        sql += " WHERE farm_id = ?"
        params.append(farm_id)
    sql += " ORDER BY assessment_date DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def delete_assessment(assessment_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
        return cur.rowcount > 0
