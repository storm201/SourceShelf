#!/usr/bin/env python3
"""
Pre-flight check. Run this before deploying, and any time something looks off.

    python3 scripts/selftest.py

It touches every endpoint and code path the automation depends on and prints a
PASS/FAIL line for each. Exit code 0 means "safe to deploy". No dependencies.
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

PASS, FAIL, WARN, SKIP = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m", \
                         "\033[33mWARN\033[0m", "\033[90mSKIP\033[0m"
results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f"  — {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


# ---------------------------------------------------------------- checks
def check_files() -> None:
    section("1. project files")
    required = [
        "index.html", "assets/app.css", "assets/app.js",
        "data/apps.json", "data/apps.js", "data/config.js",
        "scripts/fetch_apps.py", "scripts/taxonomy.py",
        "scripts/build_single.py", "scripts/supabase_store.py",
        ".github/workflows/refresh.yml", "supabase/schema.sql",
    ]
    for f in required:
        p = ROOT / f
        record(PASS if p.exists() else FAIL, f,
               "" if p.exists() else "missing")
    for f in ("update.sh", "update.bat"):
        record(PASS if (ROOT / f).exists() else WARN, f, "")


def check_data() -> dict:
    section("2. dataset")
    p = ROOT / "data" / "apps.json"
    if not p.exists():
        record(FAIL, "data/apps.json", "run scripts/fetch_apps.py")
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        record(FAIL, "data/apps.json", f"invalid JSON: {e}")
        return {}
    apps, meta = d.get("apps") or [], d.get("meta") or {}
    record(PASS if apps else FAIL, "parses as JSON", f"{len(apps)} apps")
    record(PASS if len(apps) > 100 else WARN, "catalog size", str(len(apps)))

    # required fields on every app
    need = {"id", "name", "owner", "url", "stars", "category", "platforms"}
    bad = [a.get("id") for a in apps[:5000] if not need.issubset(a)]
    record(PASS if not bad else FAIL, "every app has core fields",
           "" if not bad else f"{len(bad)} malformed, e.g. {bad[:3]}")

    # history bookkeeping
    has_fs = sum(1 for a in apps if a.get("firstSeen"))
    record(PASS if has_fs == len(apps) else WARN, "firstSeen recorded",
           f"{has_fs}/{len(apps)}")
    if meta.get("seedRun"):
        record(WARN, "this is a seeding run",
               "arrivals start appearing on the next run")
    elif meta.get("baseline"):
        record(PASS, "baseline exists", f"baselineDate={meta.get('baselineDate')}")
    else:
        record(WARN, "no baseline yet", "first run")

    n_new = meta.get("newToday", 0)
    groups = meta.get("newArrivals") or []
    total = sum(len(g.get("apps") or []) for g in groups)
    record(PASS if total == n_new else WARN, "newToday matches arrivals",
           f"newToday={n_new}, in groups={total}")

    # no duplicates
    ids = [a["id"] for a in apps]
    record(PASS if len(ids) == len(set(ids)) else FAIL, "no duplicate ids",
           "" if len(ids) == len(set(ids)) else f"{len(ids)-len(set(ids))} dupes")

    with_dl = sum(1 for a in apps if a.get("release") and a["release"].get("assets"))
    record(PASS if with_dl else WARN, "download links resolved", f"{with_dl} apps")

    gen = meta.get("generatedAt", "")
    try:
        age = (datetime.now(gen and __import__("datetime").timezone.utc)
               - datetime.fromisoformat(gen)).days
        record(PASS if age <= 2 else WARN, "data freshness", f"{age}d old")
    except Exception:
        record(WARN, "data freshness", "no generatedAt")
    return d


def check_build() -> None:
    section("3. build output")
    out = ROOT / "sourceshelf.html"
    if not out.exists():
        record(FAIL, "sourceshelf.html", "run scripts/build_single.py")
        return
    html = out.read_text(encoding="utf-8")
    kb = len(html.encode()) / 1024
    record(PASS, "sourceshelf.html exists", f"{kb:.0f} KB")
    checks = [
        ("CSS inlined", "<style>" in html and "--accent" in html and ".grid.g3" in html),
        ("dataset inlined", "window.__SOURCESHELF__=" in html),
        ("config inlined", "window.__SUPABASE__" in html),
        ("app js inlined", "SOURCESHELF" in html and "_trend" in html),
        ("no external <script src>", 'src="assets/' not in html),
        ("no external stylesheet", 'href="assets/' not in html),
    ]
    for name, ok in checks:
        record(PASS if ok else FAIL, name)

    for f, label in (("dist/index.html", "dist page"),
                     ("dist/data/new-arrivals.json", "new-arrivals endpoint"),
                     ("dist/feed.xml", "RSS feed")):
        p = ROOT / f
        record(PASS if p.exists() else WARN, label,
               f"{p.stat().st_size} B" if p.exists()
               else "not built yet — update.py creates dist/")

    na = ROOT / "dist/data/new-arrivals.json"
    if na.exists():
        try:
            doc = json.loads(na.read_text(encoding="utf-8"))
            record(PASS, "new-arrivals.json parses",
                   f"{doc.get('count')} day groups")
        except Exception as e:
            record(FAIL, "new-arrivals.json", str(e))

    readme = ROOT / "README.md"
    apps_json = ROOT / "data" / "apps.json"
    if readme.exists() and apps_json.exists():
        try:
            m = json.loads(apps_json.read_text(encoding="utf-8")).get("meta", {})
            expected = f"{m.get('count', 0):,} apps"
            readme_text = readme.read_text(encoding="utf-8")
            record(PASS if expected in readme_text else WARN,
                   "README catalog count synced",
                   f"found {expected}" if expected in readme_text else f"expected {expected}")
        except Exception as e:
            record(WARN, "README catalog check", str(e))


def check_supabase() -> None:
    section("4. Supabase")
    import envcfg
    loaded = envcfg.load_dotenv()
    if loaded:
        record(PASS, ".env loaded", ", ".join(loaded))

    raw_url = envcfg.get("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    url = envcfg.normalize_url(raw_url)
    if not url:
        record(SKIP, "SUPABASE_URL", "not configured — site works statically")
        record(SKIP, "history", "local data/apps.json will be used")
        return

    record(PASS, "SUPABASE_URL", url)
    if url != raw_url.rstrip("/"):
        record(WARN, "SUPABASE_URL had an API suffix",
               f"{raw_url!r} — using {url!r} (harmless, but tidy it in .env)")
    import supabase_store
    ok, problems = supabase_store.check(verbose=False)
    if ok:
        record(PASS, "REST endpoint reachable")
        record(PASS, "apps table readable")
        if envcfg.has_write_credentials():
            record(PASS, "write access (service key)")
    else:
        for p in problems:
            record(FAIL, "supabase", p)

    if not envcfg.has_write_credentials():
        record(WARN, "SUPABASE_SERVICE_KEY",
               "needed for the automation to write; anon key is read-only")

    store = supabase_store.connect()
    if store and ok:
        try:
            rows = store.select("apps", {"select": "id", "limit": 1000},
                                paginate=True)
            record(PASS, "rows stored", str(len(rows)))
        except Exception as e:
            record(FAIL, "row count", str(e)[:120])


def check_github_api() -> None:
    section("5. GitHub API")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    req = urllib.request.Request(
        "https://api.github.com/rate_limit",
        headers={"User-Agent": "sourceshelf-selftest",
                 **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        core = d["resources"]["core"]
        search = d["resources"]["search"]
        record(PASS, "api.github.com reachable")
        record(PASS, "core quota", f"{core['remaining']}/{core['limit']}")
        record(PASS if search["remaining"] > 5 else WARN, "search quota",
               f"{search['remaining']}/{search['limit']}")
        if not token:
            record(WARN, "GITHUB_TOKEN", "unset — crawl is slow and rate-limited")
    except Exception as e:
        record(FAIL, "api.github.com", str(e)[:120])


def check_workflow() -> None:
    section("6. GitHub Actions workflow")
    p = ROOT / ".github/workflows/refresh.yml"
    if not p.exists():
        record(FAIL, "refresh.yml", "missing")
        return
    text = p.read_text(encoding="utf-8")
    record(PASS, "workflow exists")
    for name, needle in [
        ("nightly schedule", 'cron:'),
        ("manual trigger", 'workflow_dispatch'),
        ("python setup", 'setup-python'),
        ("crawler step", 'fetch_apps.py'),
        ("build step", 'build_single.py'),
        ("pages deploy", 'deploy-pages'),
        ("pages artifact", 'upload-pages-artifact'),
        ("supabase secrets", 'SUPABASE_SERVICE_KEY'),
    ]:
        record(PASS if needle in text else WARN, name,
               "" if needle in text else "not found")
    try:
        import yaml  # optional
        yaml.safe_load(text)
        record(PASS, "valid YAML")
    except ImportError:
        # No parser installed. Fall back to the structural checks that actually
        # catch the mistakes humans make: tabs, missing sections, bad indents.
        problems = []
        if "\t" in text:
            problems.append("tab character (YAML forbids tabs)")
        for need in ("on:", "jobs:", "runs-on:", "steps:"):
            if need not in text:
                problems.append(f"missing '{need}'")
        if not text.startswith(("name:", "#")):
            problems.append("file should start with 'name:'")
        record(WARN if problems else PASS, "structure ok",
               "; ".join(problems) if problems else "no parser installed — structure only")
    except Exception as e:
        record(FAIL, "valid YAML", str(e)[:120])


def main() -> int:
    print("\033[1mSourceShelf — self test\033[0m")
    print(f"root: {ROOT}")
    check_files()
    check_data()
    check_build()
    check_supabase()
    check_github_api()
    check_workflow()

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    skips = [r for r in results if r[0] == SKIP]
    print("\n" + "=" * 62)
    print(f"  {len(results) - len(fails) - len(warns) - len(skips)} passed · "
          f"{len(warns)} warnings · {len(skips)} skipped · {len(fails)} failed")
    if fails:
        print("\n  \033[31mBlocking problems:\033[0m")
        for _, name, detail in fails:
            print(f"    - {name}: {detail}")
    print("=" * 62)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
