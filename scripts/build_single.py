#!/usr/bin/env python3
"""
Build step. Produces every deployable artifact in one pass:

    sourceshelf.html          single self-contained page (double-click, or host anywhere)
    dist/index.html         same page, used by the GitHub Pages deploy
    dist/data/*             multi-file assets for Pages (config, JSON, feed)
    dist/data/new-arrivals.json   public endpoint: newest apps, day by day
    dist/feed.xml           RSS feed of new arrivals
    data/config.js          runtime Supabase config (committed default = null)

Supabase keys are injected at build time from the environment:
    SUPABASE_URL + SUPABASE_ANON_KEY   → safe to ship (read-only, RLS enforced)
Never put the service key here: it must stay in Actions secrets only.
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


# --------------------------------------------------------------------- config
def supabase_client_config() -> dict | None:
    # Load .env here too: build_single.py is normally run as a *child* process
    # of update.py, and a .env loaded by the parent's Python process is not
    # visible to a fresh interpreter. Without this, `python scripts/update.py`
    # built a site with "supabase config: none" even though .env was filled in,
    # so the deployed page could never reach the database.
    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import envcfg
        envcfg.load_dotenv()
    except Exception:
        pass

    url = (os.environ.get("SUPABASE_URL")
           or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").strip().rstrip("/")
    for _suffix in ("/rest/v1", "/rest", "/auth/v1", "/storage/v1"):
        if url.endswith(_suffix):
            url = url[: -len(_suffix)].rstrip("/")
    key = (os.environ.get("SUPABASE_ANON_KEY")
           or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or "").strip()
    if not url or not key:
        return None
    return {"url": url, "anonKey": key}


def write_config(cfg: dict | None) -> None:
    body = ("/* Runtime configuration, rewritten by scripts/build_single.py.\n"
            "   Committed as null so the site works offline and never 404s. */\n")
    body += ("window.__SUPABASE__ = null;\n" if not cfg
             else "window.__SUPABASE__ = " + json.dumps(cfg, separators=(",", ":")) + ";\n")
    (ROOT / "data" / "config.js").write_text(body, encoding="utf-8")


# ------------------------------------------------------------------ endpoints
def write_new_arrivals_json(payload: dict) -> Path:
    """A stable public endpoint listing what was added, newest day first."""
    meta = payload.get("meta", {})
    doc = {
        "generatedAt": meta.get("generatedAt"),
        "count": len(meta.get("newArrivals") or []),
        "days": meta.get("newArrivals") or [],
    }
    out = DIST / "data" / "new-arrivals.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return out


def write_feed(payload: dict) -> Path | None:
    """RSS 2.0 feed — subscribe in any reader to hear about new apps."""
    meta = payload.get("meta", {})
    days = meta.get("newArrivals") or []
    if not days:
        return None
    site = os.environ.get("SITE_URL", "").strip().rstrip("/")
    items = []
    for g in days[:7]:
        for a in (g.get("apps") or [])[:40]:
            link = a.get("url") or f"https://github.com/{a['id']}"
            pub = f"{g['date']}T06:00:00+00:00"
            desc = a.get("description") or ""
            items.append(
                "    <item>\n"
                f"      <title>{xml_escape(a['name'])} — {xml_escape(a['category'])}</title>\n"
                f"      <link>{xml_escape(link)}</link>\n"
                f"      <guid isPermaLink=\"false\">{xml_escape(a['id'])}-{g['date']}</guid>\n"
                f"      <pubDate>{pub}</pubDate>\n"
                f"      <description>{xml_escape(desc)} (★ {a.get('stars', 0):,})</description>\n"
                "    </item>")
    gen = meta.get("generatedAt") or datetime.now(timezone.utc).isoformat()
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>\n'
        "  <title>SourceShelf — new arrivals</title>\n"
        f"  <link>{xml_escape(site or 'https://github.com')}/</link>\n"
        "  <description>Open-source apps newly discovered by the nightly crawler</description>\n"
        f"  <lastBuildDate>{gen}</lastBuildDate>\n"
        + "\n".join(items) + "\n</channel></rss>\n")
    out = DIST / "feed.xml"
    out.write_text(xml, encoding="utf-8")
    return out


# -------------------------------------------------------------------- html
def build_html() -> tuple[str, dict]:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "assets/app.css").read_text(encoding="utf-8")
    js = (ROOT / "assets/app.js").read_text(encoding="utf-8")
    cfg = (ROOT / "data" / "config.js").read_text(encoding="utf-8")
    data = (ROOT / "data" / "apps.js").read_text(encoding="utf-8")

    payload = data.split("=", 1)[1].rstrip().rstrip(";")
    meta = json.loads(payload)["meta"]

    html = html.replace('<link rel="stylesheet" href="assets/app.css">',
                        f"<style>\n{css}\n</style>")
    # config must be inlined BEFORE the dataset/app script
    html = html.replace('<script src="data/config.js"></script>',
                        f"<script>\n{cfg}\n</script>")
    html = html.replace('<script src="data/apps.js"></script>',
                        f"<script>window.__SOURCESHELF__={payload};</script>")
    html = html.replace('<script src="assets/app.js"></script>',
                        f"<script>\n{js}\n</script>")
    html = html.replace("</title>",
                        f'</title>\n<meta name="generated" content="{meta.get("generatedAt", "")}">')
    return html, meta


def main() -> int:
    cfg = supabase_client_config()
    write_config(cfg)

    if not (ROOT / "data" / "apps.json").exists():
        print("!! data/apps.json missing — run scripts/fetch_apps.py first")
        return 1
    payload = json.loads((ROOT / "data" / "apps.json").read_text(encoding="utf-8"))
    meta = payload.get("meta", {})

    html, meta = build_html()
    out = ROOT / "sourceshelf.html"
    out.write_text(html, encoding="utf-8")
    kb = len(html.encode()) / 1024

    # ---- Pages artifact (self-contained page + static extras)
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "data").mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(html, encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    (DIST / "data" / "apps.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    (DIST / "data" / "config.js").write_text((ROOT / "data" / "config.js").read_text(encoding="utf-8"))

    arrivals = write_new_arrivals_json(payload)
    feed = write_feed(payload)

    # ---- report
    print(f"wrote {out.name}  ({kb:.0f} KB, {meta.get('count')} apps, "
          f"{meta.get('withDownloads', 0)} with downloads)")
    print(f"wrote dist/index.html + dist/data/apps.json")
    print(f"wrote {arrivals.relative_to(ROOT)} "
          f"({sum(len(d['apps']) for d in (meta.get('newArrivals') or []))} arrivals)")
    if feed:
        print(f"wrote {feed.relative_to(ROOT)}")
    print(f"supabase config: {'injected (' + cfg['url'] + ')' if cfg else 'none (static only)'}")
    n_new = meta.get("newToday") or 0
    print(f"new today: {n_new} · history: {meta.get('historySource', 'none')}"
          + ("" if meta.get("baseline", True) else " (baseline run)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
