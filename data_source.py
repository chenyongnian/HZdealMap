from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SAMPLE_SOURCE = Path(__file__).resolve().parent / "data" / "source_sample.json"


def _fetch_source(source_url: str | None) -> list[dict[str, Any]]:
    if source_url:
        req = Request(source_url, headers={"User-Agent": "HZdealMap/1.0"})
        with urlopen(req, timeout=20) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
    else:
        payload = json.loads(SAMPLE_SOURCE.read_text(encoding="utf-8"))

    projects = payload.get("projects") if isinstance(payload, dict) else payload
    if not isinstance(projects, list):
        raise ValueError("Data source format error: expected a 'projects' list")

    required = {
        "name",
        "district",
        "lat",
        "lng",
        "monthly_deals",
        "quarterly_deals",
        "yearly_deals",
    }
    for idx, item in enumerate(projects):
        if not isinstance(item, dict):
            raise ValueError(f"Record {idx} is not an object")
        miss = required - set(item.keys())
        if miss:
            raise ValueError(f"Record {idx} missing fields: {sorted(miss)}")
    return projects


def load_and_store_projects(db_path: Path, source_url: str | None) -> int:
    projects = _fetch_source(source_url)
    now = datetime.now(tz=timezone.utc).isoformat()
    source_desc = source_url or "local_sample_json"

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM projects")
        for p in projects:
            conn.execute(
                """
                INSERT INTO projects (
                    name, district, lat, lng,
                    monthly_deals, quarterly_deals, yearly_deals,
                    source, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["name"],
                    p["district"],
                    float(p["lat"]),
                    float(p["lng"]),
                    int(p["monthly_deals"]),
                    int(p["quarterly_deals"]),
                    int(p["yearly_deals"]),
                    source_desc,
                    now,
                ),
            )
        conn.commit()
    return len(projects)
