#!/usr/bin/env python3
"""Doctor: tell you exactly which copy of SourceShelf you are looking at.

    python scripts/doctor.py

Answers three questions that cause most confusion:

  1. Which folder am I in, and is it the one I think it is?
  2. Is this copy the current design or an older one?
  3. Is this copy built to talk to Supabase, or to a static JSON snapshot?

It also looks next to this folder for other copies of the project, because
having two of them is the single most common reason a page "refuses" to update.
"""

from __future__ import annotations

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OK = "  ok   "
BAD = "  FAIL "
WARN = "  warn "


def when(p: Path) -> str:
    if not p.exists():
        return "missing"
    return dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b %H:%M")


def looks_current() -> tuple[bool, str]:
    """Detect the shipped design by markers only it contains.

    The page is one CSS file + one JS file + one HTML file, so a half-updated
    copy (new HTML, old CSS) shows up here instead of as a mystery on screen.
    """
    css = ROOT / "assets" / "app.css"
    js = ROOT / "assets" / "app.js"
    index = ROOT / "index.html"
    marks = []
    if css.exists():
        body = css.read_text(encoding="utf-8", errors="replace")
        marks.append(".card {" in body and ".grid.g3" in body)
    if js.exists():
        body = js.read_text(encoding="utf-8", errors="replace")
        marks.append('closest(".card")' in body and 'function cardHTML' in body)
    if index.exists():
        body = index.read_text(encoding="utf-8", errors="replace")
        marks.append('class="grid g3" id="grid"' in body)
    hits = sum(1 for m in marks if m)
    return (hits == len(marks) and hits > 0,
            f"{hits}/{len(marks)} page-file markers found")


def storage_state() -> tuple[str, str]:
    cfg = ROOT / "data" / "config.js"
    if not cfg.exists():
        return "missing", "data/config.js does not exist"
    body = cfg.read_text(encoding="utf-8", errors="replace")
    if "window.__SUPABASE__ = null" in body or "window.__SUPABASE__=null" in body:
        return "static", "build has no Supabase config (page will say JSON snapshot)"
    if "supabase.co" in body:
        return "live", "build is configured for Supabase"
    return "live", "build has a Supabase config"


def siblings() -> list[Path]:
    """Other folders next to this one that look like copies of the project."""
    out = []
    try:
        for p in ROOT.parent.iterdir():
            if not p.is_dir() or p.resolve() == ROOT.resolve():
                continue
            if p.name.lower() in {"node_modules", ".git", "__pycache__", "dist"}:
                continue
            if (p / "index.html").exists() and (p / "assets" / "app.js").exists():
                out.append(p)
    except OSError:
        pass
    return out


def main() -> int:
    print()
    print("SourceShelf doctor")
    print("=" * 58)
    print(f"This copy : {ROOT}")
    print()

    print("Files")
    for rel in ("index.html", "sourceshelf.html", "assets/app.css",
                "assets/app.js", "data/config.js", "data/apps.json", ".env"):
        p = ROOT / rel
        stamp = when(p)
        mark = OK if p.exists() else (BAD if rel in ("index.html", "assets/app.js") else WARN)
        note = "" if rel != ".env" else ("  (present)" if p.exists() else "  (absent)")
        print(f"{mark}{rel:<20} {stamp}{note}")
    print()

    current, detail = looks_current()
    print("Design")
    print(f"{OK if current else BAD}{detail}")
    if not current:
        print("       This is an OLDER copy of the project. Find the newer one,")
        print("       or re-extract the zip into an empty folder.")
    print()

    kind, note = storage_state()
    print("Storage")
    mark = OK if kind == "live" else WARN
    print(f"{mark}{note}")
    if kind == "live":
        print("       After: python scripts/build_single.py  the page should")
        print("       read 'Live - Supabase' in the top right.")
    else:
        print("       Fix: make sure .env has SUPABASE_URL + SUPABASE_ANON_KEY,")
        print("       then run: python scripts/build_single.py")
    print()

    others = siblings()
    print("Other copies nearby")
    if not others:
        print(f"{OK}none found in {ROOT.parent}")
    else:
        for p in others:
            c, _ = looks_current_at(p)
            print(f"{BAD}{p}")
            print(f"       {'current design' if c else 'OLDER design'}  "
                  f"index.html {when(p / 'index.html')}")
        print()
        print("       Two copies is the usual reason a page refuses to update.")
        print("       You are serving THIS one; you may be opening THAT one.")
        print("       Delete or rename the other, then open this folder again.")
    print()

    print("=" * 58)
    print("Serve this copy with:  python scripts/serve.py")
    print()
    return 0


def looks_current_at(p: Path) -> tuple[bool, str]:
    css = p / "assets" / "app.css"
    try:
        return (".acard" in css.read_text(encoding="utf-8", errors="replace")), ""
    except OSError:
        return False, ""


if __name__ == "__main__":
    sys.exit(main())
