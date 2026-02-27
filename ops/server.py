from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "ops.db"

OPS_USER = os.getenv("AGENTTEST_OPS_USER", "ameen")
OPS_PASS = os.getenv("AGENTTEST_OPS_PASS", "changeme")

TOKENS: set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            create table if not exists leads (
              id text primary key,
              company text not null,
              contact text,
              channel text,
              value integer default 0,
              notes text,
              stage text not null,
              created_at text not null
            );

            create table if not exists tasks (
              id text primary key,
              title text not null,
              owner text,
              priority text,
              due_date text,
              notes text,
              stage text not null,
              created_at text not null
            );
            """
        )

        lead_count = conn.execute("select count(*) from leads").fetchone()[0]
        task_count = conn.execute("select count(*) from tasks").fetchone()[0]

        if lead_count == 0:
            conn.execute(
                "insert into leads (id, company, contact, channel, value, notes, stage, created_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    secrets.token_hex(8),
                    "Example AI Agency",
                    "Founder",
                    "LinkedIn",
                    18500,
                    "Pitch Setup Sprint",
                    "Lead",
                    now_iso(),
                ),
            )
        if task_count == 0:
            conn.execute(
                "insert into tasks (id, title, owner, priority, due_date, notes, stage, created_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    secrets.token_hex(8),
                    "Finalize landing page copy",
                    "Ameen",
                    "High",
                    "",
                    "Use pain-first headline",
                    "Todo",
                    now_iso(),
                ),
            )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _auth_ok(self) -> bool:
        if self.path == "/api/login" or self.path == "/api/health":
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        token = header.replace("Bearer ", "", 1).strip()
        return token in TOKENS

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._json(200, {"ok": True})

        if path.startswith("/api/"):
            if not self._auth_ok():
                return self._json(401, {"error": "unauthorized"})

            if path == "/api/state":
                with get_db() as conn:
                    leads = [dict(r) for r in conn.execute("select * from leads order by created_at desc").fetchall()]
                    tasks = [dict(r) for r in conn.execute("select * from tasks order by created_at desc").fetchall()]
                return self._json(200, {"leads": leads, "tasks": tasks})

            return self._json(404, {"error": "not found"})

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_json()

        if path == "/api/login":
            if data.get("username") == OPS_USER and data.get("password") == OPS_PASS:
                token = secrets.token_urlsafe(24)
                TOKENS.add(token)
                return self._json(200, {"token": token})
            return self._json(401, {"error": "invalid credentials"})

        if not self._auth_ok():
            return self._json(401, {"error": "unauthorized"})

        if path == "/api/leads":
            item_id = secrets.token_hex(8)
            with get_db() as conn:
                conn.execute(
                    "insert into leads (id, company, contact, channel, value, notes, stage, created_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item_id,
                        str(data.get("company", "")).strip(),
                        str(data.get("contact", "")).strip(),
                        str(data.get("channel", "Other")).strip(),
                        int(data.get("value", 0) or 0),
                        str(data.get("notes", "")).strip(),
                        "Lead",
                        now_iso(),
                    ),
                )
            return self._json(201, {"id": item_id})

        if path == "/api/tasks":
            item_id = secrets.token_hex(8)
            with get_db() as conn:
                conn.execute(
                    "insert into tasks (id, title, owner, priority, due_date, notes, stage, created_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item_id,
                        str(data.get("title", "")).strip(),
                        str(data.get("owner", "")).strip(),
                        str(data.get("priority", "Medium")).strip(),
                        str(data.get("dueDate", "")).strip(),
                        str(data.get("notes", "")).strip(),
                        "Todo",
                        now_iso(),
                    ),
                )
            return self._json(201, {"id": item_id})

        return self._json(404, {"error": "not found"})

    def do_PATCH(self):
        path = urlparse(self.path).path
        data = self._read_json()

        if not self._auth_ok():
            return self._json(401, {"error": "unauthorized"})

        if path.startswith("/api/leads/") and path.endswith("/stage"):
            item_id = path.split("/")[3]
            with get_db() as conn:
                conn.execute("update leads set stage=? where id=?", (str(data.get("stage", "Lead")), item_id))
            return self._json(200, {"ok": True})

        if path.startswith("/api/tasks/") and path.endswith("/stage"):
            item_id = path.split("/")[3]
            with get_db() as conn:
                conn.execute("update tasks set stage=? where id=?", (str(data.get("stage", "Todo")), item_id))
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        return


def main() -> None:
    init_db()
    port = int(os.getenv("AGENTTEST_OPS_PORT", "8787"))
    host = os.getenv("AGENTTEST_OPS_HOST", "127.0.0.1")
    print(f"AgentTest Ops server running at http://{host}:{port}")
    if OPS_PASS == "changeme":
        print("WARNING: AGENTTEST_OPS_PASS is default. Set a secure password before exposing this.")
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
