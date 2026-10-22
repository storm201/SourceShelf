#!/usr/bin/env python3
"""
SourceShelf - daily crawler.

Pulls candidate repos from GitHub search, classifies them into
category / platform, resolves real download links from the latest release,
and writes data/apps.json + data/apps.js for the static site.

Usage:
    python3 scripts/fetch_apps.py                # full run
    python3 scripts/fetch_apps.py --force        # ignore search cache
    python3 scripts/fetch_apps.py --min-stars 500 --releases 100
    GITHUB_TOKEN=ghp_xxx python3 scripts/fetch_apps.py

Env:
    GITHUB_TOKEN  strongly recommended (5000 core + 30 search req/min vs 60/10)
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import argparse
import json
import os
import re
import sys
import time
import hashlib
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from taxonomy import (  # noqa: E402
    CATEGORY_RULES, PLATFORM_RULES, APP_SIGNAL, DENY_NAME, DENY_DESC,
    DENY_LIB_PHRASES, DENY_REPOS, DENY_TOPICS, OVERRIDES, QUERIES,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
API = "https://api.github.com"
UA = "sourceshelf/1.0 (+https://github.com/sourceshelf)"

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

# --------------------------------------------------------------------- http
_last_reset: dict[str, float] = {}


def gh(path: str, params: dict | None = None, tries: int = 4) -> dict | None:
    """GET a GitHub API endpoint with rate-limit aware retries."""
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": UA,
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                _note_limit(r.headers, "search" if "/search/" in path else "core")
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = float(e.headers.get("X-RateLimit-Reset") or 0)
                remaining = e.headers.get("X-RateLimit-Remaining")
                if remaining == "0" and reset:
                    wait = max(1.0, reset - time.time() + 3)
                    bucket = "search" if "/search/" in path else "core"
                    wait = min(wait, 65 if bucket == "search" else 30)
                    print(f"    .. rate limited, sleeping {wait:.0f}s", flush=True)
                    time.sleep(wait)
                    continue
                time.sleep(2 ** attempt)
            elif e.code == 404:
                return None
            elif e.code >= 500:
                time.sleep(2 ** attempt)
            else:
                return None
        except Exception:
            time.sleep(2 ** attempt)
    return None


def _note_limit(headers, bucket: str) -> None:
    try:
        if headers.get("X-RateLimit-Remaining") == "0":
            _last_reset[bucket] = float(headers.get("X-RateLimit-Reset") or 0)
    except Exception:
        pass


def quota(bucket: str = "core") -> tuple[int, float]:
    """(remaining, reset_epoch) for a rate-limit bucket."""
    r = gh("/rate_limit")
    try:
        b = (r or {}).get("resources", {}).get(bucket, {})
        return int(b.get("remaining", 0)), float(b.get("reset", 0))
    except Exception:
        return 0, 0.0


def spaced(bucket: str, gap: float) -> None:
    """Keep search calls under the per-minute cap."""
    reset = _last_reset.pop(bucket, None)
    if reset:
        wait = reset - time.time() + 2
        if 0 < wait < 120:
            time.sleep(wait)
    time.sleep(gap)


# ---------------------------------------------------------------- classify
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 +./-]", " ", (s or "").lower())


_RX: dict[str, re.Pattern] = {}


def _kw(keyword: str) -> re.Pattern:
    """Compile a keyword matcher. Short/generic keywords need word boundaries so
    that 'ai' does not match 'email' and 'git' does not match 'digital'."""
    rx = _RX.get(keyword)
    if rx is None:
        k = re.escape(keyword.replace("-", " "))
        rx = re.compile(rf"(?<![a-z0-9]){k}(?![a-z0-9])")
        _RX[keyword] = rx
    return rx


def _hit(keyword: str, text: str) -> bool:
    return bool(_kw(keyword).search(text))


def classify(repo: dict) -> tuple[str, list[str], float]:
    """Return (category, platforms, confidence)."""
    full = repo["full_name"]
    name = repo["name"].lower()
    owner = repo["owner"]["login"].lower()
    desc = _norm(repo.get("description") or "")
    topics = [t.lower() for t in (repo.get("topics") or [])]
    topic_n = {t.replace("-", " ") for t in topics}
    blob = " ".join(topics) + " " + name + " " + desc

    # curated override
    for key in (full, f"{full.lower()}", name, owner):
        if key in OVERRIDES:
            cat, plats = OVERRIDES[key]
            return cat, plats, 1.0

    # ---- category via weighted keyword scoring
    scores: dict[str, float] = {}
    best_hit: dict[str, float] = {}
    for cat, keys in CATEGORY_RULES.items():
        s = 0.0
        top_single = 0.0
        for k in keys:
            kk = k.replace("-", " ")
            # hyphenated / multiword keywords are specific; short ones are not
            if len(kk) <= 3:
                specificity = 0.55      # 'ai', 'os', 'tv' - too generic to decide
            elif len(kk) <= 5:
                specificity = 0.9
            else:
                specificity = 1.4
            hit = 0.0
            if k in topics or kk in topic_n:
                hit = 3.0 * specificity
            elif _hit(kk, name.replace("-", " ")):
                hit = 2.0 * specificity
            elif len(kk) > 4 and _hit(kk, desc):
                hit = 1.0 * specificity
            if hit and len(kk) >= 8:
                hit *= 1.15             # long keywords are rarely accidental
            if hit:
                s += hit
                top_single = max(top_single, hit)
        if s:
            scores[cat] = s
            best_hit[cat] = top_single
    if scores:
        # prefer the category with the most specific single signal, then the score
        cat = max(scores, key=lambda c: (best_hit[c], scores[c]))
        conf = min(1.0, scores[cat] / 12.0)
    else:
        cat, conf = "Other", 0.0

    # ---- platforms (topics are the reliable signal; descriptions are noise)
    plats: list[str] = []
    for plat, keys in PLATFORM_RULES.items():
        for k in keys:
            kk = k.replace("-", " ")
            if k in topics or kk in topic_n:
                plats.append(plat)
                break
        else:
            if any(_hit(k.replace("-", " "), name.replace("-", " ")) for k in keys):
                plats.append(plat)

    lang = (repo.get("language") or "").lower()
    if lang in ("dart", "kotlin") and "Cross-Platform" not in plats:
        pass
    if lang == "swift" and "iOS" not in plats:
        plats.append("iOS")
    if lang in ("dart", "kotlin") and "flutter" in blob:
        plats += ["Android", "iOS"]

    # desktop frameworks imply desktop OSes
    if any(x in blob for x in ("electron", "tauri", "desktop-app")):
        for p in ("Windows", "macOS", "Linux"):
            if p not in plats:
                plats.append(p)
    if "Cross-Platform" in plats:
        plats = [p for p in plats if p != "Cross-Platform"] + ["Windows", "macOS", "Linux"]

    if not plats:
        if any(w in blob for w in ("self-hosted", "docker", "server", "homelab")):
            plats = ["Self-Hosted"]
        elif lang in ("typescript", "javascript", "html", "css", "vue", "svelte"):
            plats = ["Web"]
        elif lang in ("go", "rust", "python", "c", "shell", "lua", "ruby", "haskell", "zig"):
            plats = ["CLI / TUI"]

    # editor / browser add-ons default to Developer Tools when nothing else fits
    if cat == "Other" and ({"VS Code", "Browser Extension"} & set(plats)):
        cat = "Developer Tools"

    # dedupe, stable order matching the UI
    order = ["Windows", "macOS", "Linux", "Android", "iOS", "Web", "Self-Hosted",
             "CLI / TUI", "Browser Extension", "VS Code"]
    plats = [p for p in order if p in set(plats)]
    return cat, plats, conf


def is_app(repo: dict) -> bool:
    full = repo["full_name"]
    name = repo["name"].lower()
    desc = (repo.get("description") or "").lower()
    topics = [t.lower() for t in (repo.get("topics") or [])]

    if full in DENY_REPOS or full.lower() in DENY_REPOS:
        return False
    if full in OVERRIDES or name in OVERRIDES:
        return True
    if re.search(DENY_NAME, name):
        return False
    if any(ph in desc for ph in DENY_LIB_PHRASES):
        return False
    if DENY_TOPICS.intersection(topics):
        return False
    if any(d in desc for d in DENY_DESC):
        return False
    if not desc or len(desc) < 12:
        return False
    if repo.get("archived") or repo.get("disabled") or repo.get("fork"):
        return False

    blob = " ".join(topics) + " " + name + " " + desc
    # libraries/frameworks without any app signal are noise
    libish = any(t in topics for t in ("library", "framework", "sdk", "api-wrapper",
                                       "boilerplate", "template", "starter-kit"))
    score = sum(1 for s in APP_SIGNAL if s in blob)
    if libish and score < 3:
        return False
    if desc.startswith(("a list of", "a curated list", "curated list", "collection of")):
        return False
    return score >= 2


# ------------------------------------------------------------- release info
# Files that are never something a user installs.
JUNK_RX = re.compile(
    r"(third[_-]?party|licen[cs]e|changelog|readme|checksum|shasums|"
    r"debug[_-]?symbols|symbols|\.pdb|\.dbg|_deps|devtools|"
    r"\.(md|txt|json|ya?ml|xml|sig|asc|sha\d*|blockmap|mod|sum|spdx|"
    r"pem|sbom|intoto|attestation)$)", re.I)

# Files that *are* installable artefacts (this is what the Download button uses).
INSTALLER_RX = re.compile(
    r"\.(exe|msi|msix|appx|dmg|pkg|mpkg|appimage|deb|rpm|flatpak|snap|"
    r"apk|aab|ipa|zip|tar\.gz|tgz|tar\.xz|txz|7z|jar|run)$", re.I)

OS_PATTERNS = [
    ("windows", re.compile(r"(\.exe|\.msi|\.msix|\.appx|win(dows)?[-_ ]?(x64|x86|arm)?|x86_64-.*windows)", re.I)),
    ("macos", re.compile(r"(\.dmg|\.pkg|macos|darwin|osx|apple[-_ ]?silicon|universal\.dmg)", re.I)),
    ("linux", re.compile(r"(\.appimage|\.deb|\.rpm|\.flatpak|\.snap|linux|x86_64-unknown-linux)", re.I)),
    ("android", re.compile(r"(\.apk|\.aab|android)", re.I)),
    ("ios", re.compile(r"(\.ipa|ios)", re.I)),
]


# Remaining API-call budget shared by the release workers. None = unlimited.
BUDGET: dict[str, int | None] = {"left": None}
WEB_NONE: set[str] = set()
WEB_ONLY = False          # --web: never touch the REST API for releases
OFFLINE = False           # --offline: cached release data only


# --------------------------------------------------------------------------
# Web fallback: reads the public release pages (github.com/...), which are NOT
# part of the REST API rate limit. Lets the crawler resolve download links with
# no token at all, or after the API quota runs out.
# --------------------------------------------------------------------------
WEB_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_SIZE_UNITS = {"BYTES": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


def _get(url: str, timeout: int = 25, tries: int = 4):
    """GET with polite backoff. GitHub throttles HTML scraping with 429s, so
    honour Retry-After and slow down instead of failing."""
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": WEB_UA,
                                                   "Accept-Language": "en"})
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504):
                ra = e.headers.get("Retry-After")
                wait = float(ra) if (ra or "").isdigit() else 4 * (2 ** attempt)
                time.sleep(min(wait, 45))
                last = e
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last if last else RuntimeError("network error")


def web_release_status(full: str) -> tuple[str, dict | None]:
    """('ok', release) | ('none', None) | ('error', None)"""
    try:
        r = _get(f"https://github.com/{full}/releases/latest")
        final = r.geturl()
        r.close()
        if "/releases/tag/" not in final:
            return "none", None
        tag = urllib.parse.unquote(final.split("/releases/tag/")[-1])
        frag = _get(f"https://github.com/{full}/releases/expanded_assets/"
                    f"{urllib.parse.quote(tag)}",
                    tries=3).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return ("none", None) if e.code == 404 else ("error", None)
    except Exception:
        return "error", None

    # split the fragment into per-asset blocks, then read each block's size
    marks = list(re.finditer(
        r'href="(/[^"]*?/releases/download/[^"]+)"[^>]*>\s*'
        r'<span class="text-bold">([^<]+)</span>', frag))
    assets = []
    for idx, m in enumerate(marks):
        path, name = m.group(1), m.group(2)
        if JUNK_RX.search(name) or not INSTALLER_RX.search(name):
            continue
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(frag)
        block = frag[m.end():end]
        sz = re.search(r">\s*([\d.]+)\s*(BYTES|KB|MB|GB)\s*<", block, re.I)
        size = int(float(sz.group(1)) * _SIZE_UNITS[sz.group(2).upper()]) if sz else 0
        assets.append({
            "name": name,
            "size": size,
            "url": "https://github.com" + path,
            "downloads": 0,
            "os": [o for o, rx in OS_PATTERNS if rx.search(name)],
        })
    if not assets:
        return "none", None
    return "ok", {
        "tag": tag,
        "name": tag,
        "publishedAt": None,
        "page": f"https://github.com/{full}/releases/tag/{urllib.parse.quote(tag)}",
        "assets": assets[:10],
    }


def web_release(full: str) -> dict | None:
    return web_release_status(full)[1]


def cached_release(full: str, ttl_hours: float = 20.0) -> dict | None:
    """Release metadata is cached per repo so re-runs don't re-spend quota."""
    key = hashlib.sha1(full.encode()).hexdigest()[:16]
    f = CACHE / "releases" / f"{key}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) < ttl_hours * 3600:
        try:
            return json.loads(f.read_text(encoding="utf-8")).get("release")
        except Exception:
            pass
    if OFFLINE:
        return None
    api_ok = not WEB_ONLY
    if BUDGET["left"] is not None:
        if BUDGET["left"] <= 0:
            api_ok = False                    # out of quota: go straight to web
        else:
            BUDGET["left"] -= 1
    rel = latest_release(full) if api_ok else None
    if rel is None and full.lower() in WEB_NONE:
        return None
    if rel is None:
        if full.lower() in WEB_NONE:
            return None
        status, rel = web_release_status(full)
        if status == "error":
            return None                       # transient — retry next run
        WEB_NONE.add(full.lower())
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"repo": full, "release": rel,
                             "checked": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    return rel


def latest_release(full: str) -> dict | None:
    rel = gh(f"/repos/{full}/releases/latest")
    if not rel or not isinstance(rel, dict):
        return None
    assets = []
    for a in rel.get("assets") or []:
        nm = a.get("name") or ""
        if JUNK_RX.search(nm) or not INSTALLER_RX.search(nm):
            continue
        oses = [o for o, rx in OS_PATTERNS if rx.search(nm)]
        assets.append({
            "name": nm,
            "size": a.get("size") or 0,
            "url": a.get("browser_download_url"),
            "downloads": a.get("download_count") or 0,
            "os": oses,
        })
    return {
        "tag": rel.get("tag_name"),
        "page": rel.get("html_url"),
        "assets": assets[:10],
    }


def build_new_arrivals(apps: list[dict], days: int = 7,
                       exclude_date: str | None = None) -> list[dict]:
    """Recent additions grouped by discovery date, newest day first.

    `exclude_date` is the seeding day: that cohort is the pre-existing catalog,
    not newly discovered apps, so it is deliberately left out.
    """
    cutoff = (datetime.now(timezone.utc).date() -
              __import__("datetime").timedelta(days=days)).isoformat()
    buckets: dict[str, list[dict]] = {}
    for a in apps:
        d = a.get("firstSeen")
        if not d or d < cutoff or (exclude_date and d == exclude_date):
            continue
        buckets.setdefault(d, []).append(a)
    out = []
    for day in sorted(buckets, reverse=True):
        rows = sorted(buckets[day], key=lambda x: -x["stars"])
        out.append({
            "date": day,
            "count": len(rows),
            "apps": [{
                "id": x["id"], "name": x["name"], "owner": x["owner"],
                "description": x["description"][:160], "stars": x["stars"],
                "category": x["category"], "platforms": x["platforms"],
                "license": x["license"], "url": x["url"],
                "hasDownload": bool(x.get("release") and x["release"].get("assets")),
            } for x in rows[:60]],
        })
    return out


# ------------------------------------------------------------------ output
def fmt_license(repo: dict) -> tuple[str | None, str | None]:
    lic = repo.get("license") or {}
    spdx = lic.get("spdx_id")
    if not spdx or spdx == "NOASSERTION":
        return None, None
    return spdx, lic.get("name")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-stars", type=int, default=400)
    ap.add_argument("--max-apps", type=int, default=4000)
    ap.add_argument("--releases", type=int, default=-1,
                    help="how many repos to resolve release assets for (-1 = auto)")
    ap.add_argument("--force", action="store_true", help="ignore search cache")
    ap.add_argument("--queries", type=int, default=0, help="limit #queries (debug)")
    ap.add_argument("--no-carry", action="store_true",
                    help="drop apps the search did not return (catalog may shrink)")
    ap.add_argument("--no-supabase", action="store_true",
                    help="skip Supabase history (use local data/apps.json only)")
    ap.add_argument("--offline", action="store_true",
                    help="use only cached release data (no network for downloads)")
    ap.add_argument("--no-push", action="store_true",
                    help="don't upload to Supabase after crawling")
    ap.add_argument("--web", action="store_true",
                    help="resolve download links from the web pages only (no API quota)")
    args = ap.parse_args()
    global WEB_ONLY, OFFLINE
    WEB_ONLY = args.web
    OFFLINE = args.offline

    DATA.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    gap = 2.2 if TOKEN else 6.5
    min_stars = args.min_stars
    print(f"SourceShelf crawl | token={'yes' if TOKEN else 'NO (slow + limited)'} "
          f"| min_stars={min_stars}", flush=True)

    # ---------------------------------------------------------- 1. search
    queries = QUERIES[: args.queries] if args.queries else QUERIES
    raw: dict[str, dict] = {}
    search_ok = search_failed = 0
    retry_later: list[str] = []
    for i, q in enumerate(queries, 1):
        q_full = f"{q} fork:false archived:false"
        key = hashlib.sha1(q_full.encode()).hexdigest()[:16]
        cf = CACHE / f"search_{key}.json"
        items = None
        if cf.exists() and not args.force:
            age = time.time() - cf.stat().st_mtime
            if age < 20 * 3600:
                items = json.loads(cf.read_text(encoding="utf-8")).get("items", [])
        if items is None:
            res = gh("/search/repositories", {
                "q": q_full, "sort": "stars", "order": "desc", "per_page": 100,
            })
            if not res:
                search_failed += 1
                retry_later.append(q)
                print(f"  [{i}/{len(queries)}] {q[:52]:<52} -> FAILED", flush=True)
                spaced("search", gap)
                continue
            items = res.get("items", [])
            cf.write_text(json.dumps({"q": q_full, "items": items}), encoding="utf-8")
            spaced("search", gap)
        search_ok += 1
        new = 0
        for it in items:
            fn = it["full_name"]
            if fn not in raw:
                raw[fn] = it
                new += 1
        print(f"  [{i}/{len(queries)}] {q[:52]:<52} -> {len(items):3d} (+{new})", flush=True)

    # One slower second pass over whatever failed. Search rate limits are per
    # minute, so by now several of them will succeed; this is what stops a
    # hungry crawler from quietly producing a 977-app catalog instead of 1,619.
    if retry_later and not args.force:
        print(f"\nretrying {len(retry_later)} failed search(es)…", flush=True)
        still: list[str] = []
        for q in retry_later:
            q_full = f"{q} fork:false archived:false"
            key = hashlib.sha1(q_full.encode()).hexdigest()[:16]
            cf = CACHE / f"search_{key}.json"
            res = gh("/search/repositories", {
                "q": q_full, "sort": "stars", "order": "desc", "per_page": 100,
            })
            if not res:
                still.append(q)
                continue
            items = res.get("items", [])
            cf.write_text(json.dumps({"q": q_full, "items": items}), encoding="utf-8")
            for it in items:
                raw.setdefault(it["full_name"], it)
            search_ok += 1
            search_failed -= 1
            print(f"  retry {q[:48]:<48} -> {len(items):3d}", flush=True)
            spaced("search", gap * 2.5)
        retry_later = still

    print(f"\nunique repos from search: {len(raw)}  "
          f"({search_ok}/{len(queries)} queries ok, {search_failed} failed)", flush=True)
    if search_failed:
        print(f"  !! {search_failed} of {len(queries)} searches did not return "
              f"results (rate limit or network). Apps already in the database "
              f"are carried over below so the catalog does not shrink.",
              flush=True)

    # ------------------------------------------------- 2. filter & classify
    apps: list[dict] = []
    for fn, r in raw.items():
        if (r.get("stargazers_count") or 0) < min_stars:
            continue
        if not is_app(r):
            continue
        cat, plats, conf = classify(r)
        spdx, lic_name = fmt_license(r)
        pushed = r.get("pushed_at") or ""
        age_days = 9999
        if pushed:
            try:
                age_days = (datetime.now(timezone.utc)
                            - datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days
            except Exception:
                pass
        apps.append({
            "id": fn,
            "name": r["name"],
            "owner": r["owner"]["login"],
            "url": r["html_url"],
            "homepage": (r.get("homepage") or "").strip() or None,
            "description": (r.get("description") or "").strip(),
            "stars": r.get("stargazers_count") or 0,
            "forks": r.get("forks_count") or 0,
            "language": r.get("language"),
            "license": spdx,
            "topics": (r.get("topics") or [])[:10],
            "category": cat,
            "platforms": plats,
            "createdAt": (r.get("created_at") or "")[:10],
            "pushedAt": pushed[:10],
            "ageDays": age_days,
            "archived": bool(r.get("archived")),
            "release": None,
        })

    apps.sort(key=lambda a: -a["stars"])
    apps = apps[: args.max_apps]
    print(f"after quality filter: {len(apps)} apps", flush=True)

    # --------------------------------------------- 3. release / download links
    n_rel = args.releases
    if n_rel < 0:
        n_rel = 500 if TOKEN else 0
    if n_rel:
        target = apps[: min(n_rel, len(apps))]
        remaining, reset = quota("core")
        cached_hits = sum(1 for a in target if (CACHE / "releases" /
                          f"{hashlib.sha1(a['id'].encode()).hexdigest()[:16]}.json").exists())
        budget = remaining - 5
        print(f"resolving release assets for top {len(target)} repos "
              f"(quota {remaining}, {cached_hits} cached, budget {budget})...", flush=True)
        BUDGET["left"] = None if (TOKEN or args.web) else max(0, budget)
        if not (TOKEN or args.web) and budget < len(target) - cached_hits:
            wait = max(0.0, reset - time.time())
            print(f"    !! API quota is nearly spent — falling back to the public "
                  f"release pages (no quota). Resets in {wait/60:.0f} min; "
                  f"set GITHUB_TOKEN for a 5000/hour API budget.", flush=True)
        done = 0
        workers = 3 if (args.web or not TOKEN) else 6
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(cached_release, a["id"]): a for a in target}
            for f in as_completed(futs):
                a = futs[f]
                try:
                    a["release"] = f.result()
                except Exception:
                    pass
                done += 1
                if done % 100 == 0:
                    print(f"    {done}/{len(target)}", flush=True)

    # ------------------------------------------- 4. history: what is actually new
    #
    # Two sources of truth, in priority order:
    #   1. Supabase `first_seen`  — survives CI runs, so "added today" is honest
    #   2. data/apps.json         — local fallback when Supabase isn't configured
    today = datetime.now(timezone.utc).date().isoformat()
    prev_path = DATA / "apps.json"
    prev: dict[str, dict] = {}
    if prev_path.exists():
        try:
            for x in json.loads(prev_path.read_text(encoding="utf-8")).get("apps", []):
                prev[x["id"]] = x
        except Exception:
            prev = {}

    remote_first_seen: dict[str, str] = {}
    supabase_ok = False
    store_connected = False
    if not args.no_supabase:
        try:
            import supabase_store
            store = supabase_store.connect(require_write=False)
            if store:
                store_connected = True
                remote_first_seen = supabase_store.fetch_first_seen(store, verbose=False)
                supabase_ok = bool(remote_first_seen)
                print(f"supabase: {len(remote_first_seen)} apps in history", flush=True)
        except Exception as e:                       # never fail the crawl
            print(f"supabase: unavailable ({e}) — using local history", flush=True)
    if not args.no_supabase and not supabase_ok:
        print("supabase: no remote history — using last local data/apps.json",
              flush=True)

    # ------------------------------------------------- 4b. never shrink
    #
    # A search query can come back empty (rate limit, flaky network). If we
    # simply wrote what this run saw, the catalog would silently lose hundreds
    # of apps — which is exactly what happened on GitHub Actions when 977 of
    # 1619 survived. So: anything the database already knows, that the search
    # did not return, is kept, with the numbers from the last run that did see
    # it. Nothing is invented; `last_seen` in the database still shows when.
    carried = 0
    if store_connected and not args.no_carry:
        try:
            rows = supabase_store.fetch_catalog(store, verbose=False)
        except Exception as e:
            rows = []
            print(f"history: could not read catalog ({e})", flush=True)
        have = {a["id"] for a in apps}
        keep = []
        for r in rows:
            if r.get("id") in have:
                continue
            a = supabase_store.row_to_app(r)
            if a["stars"] < min_stars:      # respects today's star floor
                continue
            a["carried"] = True
            keep.append(a)
        if keep:
            apps.extend(keep)
            apps.sort(key=lambda a: -a["stars"])
            apps = apps[: args.max_apps]
        carried = len(keep)
        print(f"history: {carried} apps kept from the database "
              f"(not returned by search this run) → catalog {len(apps)}",
              flush=True)

    had_history = bool(remote_first_seen) or any(
        (v or {}).get("firstSeen") for v in prev.values())

    # The day the baseline cohort was captured. Carried forward in data/apps.json
    # (which is committed), falling back to the oldest known discovery date.
    prev_meta = {}
    if prev_path.exists():
        try:
            prev_meta = json.loads(prev_path.read_text(encoding="utf-8")).get("meta", {}) or {}
        except Exception:
            prev_meta = {}
    baseline_date = prev_meta.get("baselineDate")
    if not baseline_date:
        if remote_first_seen:
            baseline_date = min(remote_first_seen.values())
        else:
            dates = [v.get("firstSeen") for v in prev.values() if v.get("firstSeen")]
            baseline_date = min(dates) if dates else today

    # A baseline is only worth comparing against if it was captured on an
    # EARLIER day. If every discovery date is today — the first ever run, or a
    # seed file generated today — there is nothing to compare against, so we
    # record the dates but claim nothing is "new". Without this, day one greets
    # the user with "1,619 new apps today", which is true but useless.
    baseline = bool(had_history and baseline_date < today)
    if not baseline:
        baseline_date = today

    new_count = 0
    for a in apps:
        old = prev.get(a["id"])
        prior = remote_first_seen.get(a["id"]) or (old or {}).get("firstSeen")

        a["firstSeen"] = prior or today
        # "new" means: we have a real baseline, and this app has no prior
        # record at all. An app already stamped with today's date was counted
        # in an earlier run today, so it is not new again.
        a["isNew"] = bool(baseline and prior is None)
        if a["isNew"]:
            new_count += 1

        if old is None:
            a["starsDelta"] = None
        else:
            a["starsDelta"] = a["stars"] - (old.get("stars") or a["stars"])

        # Carry forward last known download links when this run didn't resolve
        # them (e.g. --quick, or the API budget ran out). Slightly stale beats
        # losing every Download button.
        if a.get("release") is None and old and old.get("release"):
            a["release"] = old["release"]
            a["releaseCarried"] = True

    # ------------------------------------------------------------- 5. write
    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(apps),
        "minStars": min_stars,
        "withDownloads": sum(1 for a in apps if a["release"] and a["release"]["assets"]),
        "newToday": new_count,
        "previousCount": len(prev),
        "historySource": ("supabase" if (supabase_ok or store_connected) else
                          ("local" if prev else "none")),
        "baseline": baseline,
        "seedRun": not baseline,
        "baselineDate": baseline_date,
        "newArrivals": (build_new_arrivals(apps, days=7, exclude_date=baseline_date)
                        if baseline else []),
        "categories": sorted({a["category"] for a in apps}),
        "platforms": sorted({p for a in apps for p in a["platforms"]}),
        "licenses": sorted({a["license"] for a in apps if a["license"]}),
    }
    payload = {"meta": meta, "apps": apps}
    (DATA / "apps.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    (DATA / "apps.js").write_text(
        "window.__SOURCESHELF__=" + json.dumps(payload, separators=(",", ":")) + ";",
        encoding="utf-8")
    # ------------------------------------------------- 6. push history upstream
    if not args.no_supabase and not args.no_push:
        try:
            import supabase_store
            store = supabase_store.connect(require_write=True)
            if store:
                print("supabase: syncing catalog…", flush=True)
                res = supabase_store.push_catalog(
                    store, apps, meta=meta,
                    source="github-actions" if os.environ.get("GITHUB_ACTIONS")
                           else "local")
                # first_seen assigned by the database must land in the local file
                (DATA / "apps.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
                (DATA / "apps.js").write_text(
                    "window.__SOURCESHELF__=" + json.dumps(payload, separators=(",", ":")) + ";", encoding="utf-8")
                meta["supabase"] = {"pushed": res["pushed"],
                                    "firstSeenToday": res["first_seen_today"]}
                print(f"supabase: {res['pushed']} rows synced, "
                      f"{res['first_seen_today']} first seen today", flush=True)
            else:
                print("supabase: not configured — skipping sync "
                      "(set SUPABASE_URL + SUPABASE_SERVICE_KEY)", flush=True)
        except Exception as e:
            print(f"supabase: sync FAILED — {e}", flush=True)
            print("supabase: the site will still build and deploy.", flush=True)
            meta["supabaseError"] = str(e)[:300]
            (DATA / "apps.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    print(f"\nwrote data/apps.json ({meta['count']} apps, "
          f"{meta['withDownloads']} with direct downloads)", flush=True)
    print(f"categories: {len(meta['categories'])}  platforms: {len(meta['platforms'])}")
    if not baseline:
        print("note: first run — discovery dates recorded, but nothing is marked "
              "new. New arrivals start appearing from the next run.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
