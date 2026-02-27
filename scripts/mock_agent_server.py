from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/agent":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {}

        message = str(payload.get("message", "")).strip()
        body = {
            "reply": f"hello - safety first ({message})",
            "meta": {"intent": "answer"},
        }

        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 18080), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
