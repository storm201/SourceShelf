#!/usr/bin/env python3
"""
Serve the site locally and open it in your browser.

    python3 scripts/serve.py              # http://localhost:8080
    python3 scripts/serve.py --port 9000 --no-open

Serving (instead of double-clicking the file) makes filter URLs like
?cat=Media+%26+Audio shareable and lets the browser cache assets properly.
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import argparse
import functools
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # always revalidate so a fresh crawl shows up on reload
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the console quiet
        if "404" in (fmt % args):
            super().log_message(fmt, *args)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    if not (ROOT / "data" / "apps.js").exists() and not (ROOT / "sourceshelf.html").exists():
        print("No catalog found. Run:  python3 scripts/update.py")
        return 1

    handler = functools.partial(Handler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True

    # Say exactly which folder and which build is being served. Without this,
    # a server left running from an older copy of the project keeps answering
    # on this port and it looks like the new build was ignored.
    page = ROOT / "index.html"
    import datetime as _dt
    when = ""
    if page.exists():
        when = _dt.datetime.fromtimestamp(page.stat().st_mtime).strftime("%d %b %H:%M")
    print(f"Serving : {ROOT}")
    if when:
        print(f"Page    : index.html  (last modified {when})")

    cfg = ROOT / "data" / "config.js"
    try:
        body = cfg.read_text(encoding="utf-8")
        live = "window.__SUPABASE__ = null" not in body
    except OSError:
        live = False
    print("Storage : " + ("Supabase (live)" if live else
          "JSON snapshot only — run: python scripts/build_single.py"))

    try:
        httpd = socketserver.TCPServer(("0.0.0.0", args.port), handler)
    except OSError:
        print()
        print(f"Port {args.port} is already in use.")
        print("Something else is serving that port — most likely an older")
        print("copy of this project still running in another window.")
        print("Close it, or start on a different port:")
        print(f"    python scripts/serve.py --port {args.port + 1}")
        return 2

    with httpd:
        url = f"http://localhost:{args.port}/"
        print(f"\nSourceShelf → {url}")
        print("Ctrl+C to stop.")
        print("Page looks out of date?  python scripts/doctor.py")
        if not args.no_open:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
