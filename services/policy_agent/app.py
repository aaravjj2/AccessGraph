"""Standalone HTTP service for converting payer-policy text into requirements."""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path

from extractor import PolicyExtractionError, extract_policy_requirements


class PolicyHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _html(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/":
            page = Path(__file__).parent / "static" / "index.html"
            self._html(HTTPStatus.OK, page.read_text(encoding="utf-8"))
            return
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "service": "policy_agent"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/policy/extract":
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            self._json(HTTPStatus.OK, extract_policy_requirements(payload))
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON"})
        except PolicyExtractionError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        # Keep demo output focused on requests rather than Python's default log format.
        print("policy_agent:", format % args)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    print(f"Policy Agent listening on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), PolicyHandler).serve_forever()
