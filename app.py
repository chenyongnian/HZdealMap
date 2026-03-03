from __future__ import annotations

import json
import os
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from data_source import load_and_store_projects

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "deals.db"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_PATH = BASE_DIR / "templates" / "dashboard.html"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                district TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                monthly_deals INTEGER NOT NULL,
                quarterly_deals INTEGER NOT NULL,
                yearly_deals INTEGER NOT NULL,
                source TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(name, lat, lng)
            );
            """
        )


def _squared_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return (lat1 - lat2) ** 2 + (lng1 - lng2) ** 2


def query_all_projects() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT name, district, lat, lng, monthly_deals, quarterly_deals, yearly_deals, source, updated_at
            FROM projects ORDER BY district, name
            """
        ).fetchall()
    return [dict(r) for r in rows]


def query_summary() -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS projects,
              COALESCE(SUM(monthly_deals), 0) AS month_total,
              COALESCE(SUM(quarterly_deals), 0) AS quarter_total,
              COALESCE(SUM(yearly_deals), 0) AS year_total,
              MAX(updated_at) AS updated_at
            FROM projects
            """
        ).fetchone()
    return dict(row)


def query_nearest(lat: float, lng: float) -> dict[str, Any]:
    rows = query_all_projects()
    if not rows:
        return {"project": None, "message": "No project data available."}

    nearest = min(rows, key=lambda r: _squared_distance(lat, lng, r["lat"], r["lng"]))
    if _squared_distance(lat, lng, nearest["lat"], nearest["lng"]) > 0.0018:
        return {"project": None, "message": "当前位置附近暂无楼盘数据"}
    return {"project": nearest}


def render_dashboard_html() -> bytes:
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = html.replace("__INITIAL_PROJECTS__", json.dumps(query_all_projects(), ensure_ascii=False))
    html = html.replace("__INITIAL_SUMMARY__", json.dumps(query_summary(), ensure_ascii=False))
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        suffix = file_path.suffix
        ctype = "text/plain; charset=utf-8"
        if suffix == ".html":
            ctype = "text/html; charset=utf-8"
        elif suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif suffix == ".json":
            ctype = "application/json; charset=utf-8"

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path_lower = parsed.path.lower()
        if path_lower in {"/", "/dashboard.html", "/dashboard.htm"}:
            body = render_dashboard_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/static/"):
            rel = parsed.path.replace("/static/", "", 1)
            return self._serve_file(STATIC_DIR / rel)
        if parsed.path == "/api/projects/all":
            return self._json({"projects": query_all_projects()})
        if parsed.path == "/api/summary":
            return self._json(query_summary())
        if parsed.path == "/api/projects":
            qs = parse_qs(parsed.query)
            try:
                lat = float(qs.get("lat", [""])[0])
                lng = float(qs.get("lng", [""])[0])
            except ValueError:
                return self._json({"error": "lat and lng are required"}, 400)
            return self._json(query_nearest(lat, lng))

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/sync-source":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        payload = json.loads(raw.decode("utf-8") or "{}")
        source_url = payload.get("source_url") or os.getenv("HZ_SOURCE_URL")

        try:
            count = load_and_store_projects(DB_PATH, source_url)
            self._json({"ok": True, "updated_records": count, "source": source_url or "local sample"})
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error": str(exc)}, 500)


def main() -> None:
    init_db()
    load_and_store_projects(DB_PATH, os.getenv("HZ_SOURCE_URL"))
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("HZdealMap running at http://0.0.0.0:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
