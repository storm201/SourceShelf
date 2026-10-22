#!/usr/bin/env python3
"""
A tiny mock of the PostgREST endpoints SourceShelf talks to.

Why: you can't run CI against a real Supabase project from a test, but you *can*
prove the crawler speaks the right protocol — correct paths, headers, upsert
params, batching and pagination. This is what tests/test_supabase.py drives.

Implements just enough for us:
    GET  /rest/v1/apps?select=id,first_seen&limit=&offset=
    GET  /rest/v1/apps?select=id&first_seen=gte.YYYY-MM-DD&order=&limit=
    POST /rest/v1/apps?on_conflict=id      (Prefer: resolution=merge-duplicates)
    POST /rest/v1/runs
    GET  /rest/v1/                      (health)
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

KEY = "test-service-key"
ANON = "test-anon-key"


class State:
    def __init__(self):
        self.apps: dict[str, dict] = {}
        self.runs: list[dict] = []
        self.requests: list[tuple[str, str, dict]] = []   # method, path, headers
        self.fail_next: int = 0


def make_server(state: State, port: int = 0) -> ThreadingHTTPServer:
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # ---- helpers
        def _cors(self):
            # Real Supabase answers cross-origin requests; the mock must too,
            # otherwise browser tests fail for reasons that never happen in prod.
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods",
                             "GET, POST, PATCH, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "apikey, authorization, content-type, prefer, "
                             "accept, accept-profile, content-profile, "
                             "x-client-info")
            self.send_header("Access-Control-Expose-Headers", "Content-Range")

        def do_OPTIONS(self):
            # CORS preflight for the custom apikey/authorization headers
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send(self, code: int, payload=None, extra=None):
            body = b"" if payload is None else json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if body:
                self.wfile.write(body)

        def log_message(self, *a):
            pass

        def _auth(self) -> bool:
            key = self.headers.get("apikey") or ""
            bearer = (self.headers.get("Authorization") or "").replace("Bearer ", "")
            if not key or key != bearer:
                self._send(401, {"message": "Invalid API key"})
                return False
            if key not in (KEY, ANON):
                self._send(401, {"message": "Invalid API key"})
                return False
            return True

        def _record(self, method):
            state.requests.append((method, self.path, dict(self.headers)))

        # ---- GET
        def do_GET(self):
            self._record("GET")
            url = urlparse(self.path)
            if url.path.rstrip("/") == "/rest/v1":
                return self._send(200, {"swagger": "2.0", "info": {"title": "mock"}})
            if not self._auth():
                return

            if url.path.startswith("/rest/v1/apps"):
                q = parse_qs(url.query)
                rows = list(state.apps.values())

                for key, vals in q.items():
                    v = vals[0]
                    if key == "first_seen" and v.startswith("gte."):
                        since = v[4:]
                        rows = [r for r in rows if str(r.get("first_seen")) >= since]

                order = q.get("order", [""])[0]
                if order:
                    for part in reversed([p.strip() for p in order.split(",")]):
                        desc = part.endswith(".desc")
                        field = part.split(".")[0]
                        rows.sort(key=lambda r: (r.get(field) is None,
                                                 r.get(field) if not isinstance(
                                                     r.get(field), str) else r.get(field)),
                                  reverse=desc)

                limit = int(q.get("limit", ["1000"])[0])
                offset = int(q.get("offset", ["0"])[0])
                page = rows[offset:offset + limit]

                select = q.get("select", ["*"])[0]
                if select != "*":
                    fields = [f.strip() for f in select.split(",")]
                    page = [{k: r.get(k) for k in fields if k in r} for r in page]

                # PostgREST reports the unpaginated total in Content-Range when
                # Prefer: count=exact is asked for. The client relies on this to
                # show a true count instead of the page size.
                extra = None
                if "count=exact" in (self.headers.get("Prefer") or ""):
                    end = offset + len(page) - 1 if page else offset
                    extra = {"Content-Range": f"{offset}-{end}/{len(rows)}"}
                return self._send(200, page, extra)

            if url.path.startswith("/rest/v1/runs"):
                return self._send(200, state.runs)

            return self._send(404, {"message": "relation does not exist",
                                    "code": "42P01"})

        # ---- POST
        def do_POST(self):
            self._record("POST")
            if not self._auth():
                return
            if state.fail_next > 0:
                state.fail_next -= 1
                return self._send(503, {"message": "temporarily unavailable"})

            url = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"[]")
            rows = body if isinstance(body, list) else [body]

            if url.path.startswith("/rest/v1/apps"):
                q = parse_qs(url.query)
                on_conflict = q.get("on_conflict", ["id"])[0]
                prefer = self.headers.get("Prefer", "")
                if "merge-duplicates" not in prefer:
                    return self._send(400, {"message": "expected upsert"})
                for r in rows:
                    k = r[on_conflict]
                    if k in state.apps:
                        # merge, but never overwrite an existing first_seen
                        merged = dict(state.apps[k])
                        prev_fs = merged.get("first_seen")
                        merged.update(r)
                        merged["first_seen"] = prev_fs or r.get("first_seen")
                        state.apps[k] = merged
                    else:
                        state.apps[k] = dict(r)
                return self._send(201, None)

            if url.path.startswith("/rest/v1/runs"):
                for r in rows:
                    r.setdefault("id", len(state.runs) + 1)
                    state.runs.append(r)
                return self._send(201, None)

            return self._send(404, {"message": "relation does not exist",
                                    "code": "42P01"})

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    return srv


def serve_in_background() -> tuple[ThreadingHTTPServer, str, State]:
    state = State()
    srv = make_server(state)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    host, port = srv.server_address
    return srv, f"http://{host}:{port}", state


if __name__ == "__main__":
    srv, url, state = serve_in_background()
    print(f"mock Supabase listening on {url}")
    print(f"  service key: {KEY}")
    print(f"  anon key:    {ANON}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()
