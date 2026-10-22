#!/usr/bin/env python3
"""
Supabase storage layer for SourceShelf — stdlib only (urllib), no pip installs.

Why Supabase here at all? One reason: **history**. The GitHub search tells you
what exists today; it cannot tell you what appeared since yesterday. Storing
`first_seen` in a real table is what makes an honest "added today" section.

Endpoints used (all PostgREST, no custom server needed):
    GET   {url}/rest/v1/apps?select=id,first_seen&limit=1000&offset=N
    POST  {url}/rest/v1/apps?on_conflict=id      (upsert)
    POST  {url}/rest/v1/runs                     (crawl log)
    GET   {url}/rest/v1/apps?select=id&limit=1   (health check)

CLI:
    python3 scripts/supabase_store.py --check    # verify credentials + schema
    python3 scripts/supabase_store.py --push     # push data/apps.json
    python3 scripts/supabase_store.py --stats
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import envcfg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "sourceshelf/1.1"
BATCH = 250          # rows per upsert request
PAGE = 1000          # PostgREST max rows per response (Supabase default)


class SupabaseError(RuntimeError):
    pass


# --------------------------------------------------------------------- base
class Store:
    def __init__(self, url: str, key: str, timeout: int = 30):
        self.url = url.rstrip("/")
        self.key = key
        self.timeout = timeout

    # ---- low level -------------------------------------------------------
    def _req(self, method: str, path: str, *, body=None, extra_headers=None,
             timeout=None) -> tuple[int, bytes]:
        url = f"{self.url}/rest/v1/{path.lstrip('/')}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": UA,
        }
        if extra_headers:
            headers.update(extra_headers)
        data = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode()

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            payload = e.read().decode("utf-8", "replace")[:500]
            raise SupabaseError(f"{method} {path} → HTTP {e.code}: {payload}") from e
        except urllib.error.URLError as e:
            raise SupabaseError(f"{method} {path} → network error: {e.reason}") from e
        except TimeoutError:
            raise SupabaseError(f"{method} {path} → timed out")

    def _retry(self, fn, tries: int = 3, backoff: float = 1.5):
        last = None
        for i in range(tries):
            try:
                return fn()
            except SupabaseError as e:
                last = e
                msg = str(e)
                # 4xx (except 429) will not fix itself — fail fast
                if any(f"HTTP {c}" in msg for c in (400, 401, 403, 404, 409)):
                    raise
                time.sleep(backoff ** i)
        raise last  # type: ignore[misc]

    # ---- reads -----------------------------------------------------------
    def select(self, table: str, params: dict, *, paginate: bool = False,
               max_rows: int = 50_000) -> list[dict]:
        """GET rows. `paginate=True` walks every page (PostgREST caps at 1000)."""
        rows: list[dict] = []
        offset = 0
        while True:
            q = dict(params)
            if paginate:
                q["limit"] = PAGE
                q["offset"] = offset
            path = f"{table}?{urllib.parse.urlencode(q, doseq=True)}"
            status, raw = self._retry(lambda p=path: self._req("GET", p))
            chunk = json.loads(raw or b"[]")
            if not isinstance(chunk, list):
                raise SupabaseError(f"GET {table} returned non-list: {str(chunk)[:200]}")
            rows.extend(chunk)
            if not paginate or len(chunk) < PAGE or len(rows) >= max_rows:
                return rows
            offset += PAGE

    def count(self, table: str, filters: str = "") -> int:
        path = f"{table}?select=id{filters}&limit=1"
        _, raw = self._req("GET", path, extra_headers={"Prefer": "count=exact"})
        return len(json.loads(raw or b"[]"))

    # ---- writes ----------------------------------------------------------
    def upsert(self, table: str, rows: list[dict], *, conflict: str = "id") -> int:
        """Insert-or-update. Returns rows sent. Batched to stay well under limits."""
        if not rows:
            return 0
        total = 0
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            path = f"{table}?on_conflict={conflict}"

            def send(c=chunk, p=path):
                return self._req("POST", p, body=c, extra_headers={
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                })

            self._retry(send)
            total += len(chunk)
        return total

    def insert(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        self._retry(lambda: self._req(
            "POST", table, body=rows, extra_headers={"Prefer": "return=minimal"}))


# ------------------------------------------------------------------ mapping
def app_to_row(a: dict) -> dict:
    """Map the crawler's app dict onto the `apps` table."""
    def as_date(v):
        if not v:
            return None
        s = str(v)[:10]
        try:
            date.fromisoformat(s)
            return s
        except ValueError:
            return None

    return {
        "id": a["id"],
        "name": a.get("name") or a["id"].split("/")[-1],
        "owner": a.get("owner") or a["id"].split("/")[0],
        "url": a.get("url") or f"https://github.com/{a['id']}",
        "homepage": a.get("homepage"),
        "description": a.get("description") or "",
        "stars": int(a.get("stars") or 0),
        "forks": int(a.get("forks") or 0),
        "language": a.get("language"),
        "license": a.get("license"),
        "category": a.get("category") or "Other",
        "platforms": list(a.get("platforms") or []),
        "topics": list(a.get("topics") or []),
        "repo_created_at": as_date(a.get("createdAt")),
        "repo_pushed_at": as_date(a.get("pushedAt")),
        "release": a.get("release"),
        # first_seen is preserved by the caller; default to today
        "first_seen": a.get("firstSeen") or date.today().isoformat(),
        "last_seen": date.today().isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------------ helpers
def connect(require_write: bool = False) -> Store | None:
    """Build a Store from env/.env. None (with a message) when not configured."""
    envcfg.load_dotenv()
    cfg = envcfg.supabase_config(require_secret=require_write)
    if not cfg:
        return None
    url, key = cfg
    if not url.startswith("http"):
        print(f"  !! SUPABASE_URL looks wrong: {url!r} (expected https://xxx.supabase.co)")
        return None
    return Store(url, key)


def fetch_first_seen(store: Store, verbose: bool = True) -> dict[str, str]:
    """id -> first_seen for every row already stored. This is the history."""
    try:
        rows = store.select("apps", {"select": "id,first_seen"}, paginate=True)
    except SupabaseError as e:
        if verbose:
            print(f"  !! could not read history: {e}")
        return {}
    out = {}
    for r in rows:
        if r.get("id") and r.get("first_seen"):
            out[r["id"]] = str(r["first_seen"])[:10]
    if verbose:
        print(f"  history: {len(out)} apps already known")
    return out


CATALOG_COLS = ("id,name,owner,url,homepage,description,stars,forks,language,"
                "license,category,platforms,topics,repo_created_at,"
                "repo_pushed_at,release,first_seen")


def fetch_catalog(store: Store, verbose: bool = True) -> list[dict]:
    """Every stored app, as rows. Used to keep the catalog from shrinking when a
    crawl comes back short (search rate limits, a failed query)."""
    try:
        rows = store.select("apps", {"select": CATALOG_COLS}, paginate=True)
    except SupabaseError as e:
        if verbose:
            print(f"  !! could not read catalog: {e}")
        return []
    return rows


def row_to_app(r: dict) -> dict:
    """Inverse of app_to_row: a DB row back into the crawler's app shape."""
    def d(v):
        return str(v)[:10] if v else ""

    pushed = d(r.get("repo_pushed_at"))
    age = 9999
    if pushed:
        try:
            age = (date.today() - date.fromisoformat(pushed)).days
        except ValueError:
            pass
    return {
        "id": r["id"],
        "name": r.get("name") or r["id"].split("/")[-1],
        "owner": r.get("owner") or r["id"].split("/")[0],
        "url": r.get("url") or f"https://github.com/{r['id']}",
        "homepage": r.get("homepage"),
        "description": r.get("description") or "",
        "stars": int(r.get("stars") or 0),
        "forks": int(r.get("forks") or 0),
        "language": r.get("language"),
        "license": r.get("license"),
        "topics": list(r.get("topics") or []),
        "category": r.get("category") or "Other",
        "platforms": list(r.get("platforms") or []),
        "createdAt": d(r.get("repo_created_at")),
        "pushedAt": pushed,
        "ageDays": age,
        "archived": False,
        "release": r.get("release"),
        "firstSeen": d(r.get("first_seen")),
    }


def fetch_new_arrivals(store: Store, days: int = 7, limit: int = 200) -> list[dict]:
    since = (date.today() - __import__("datetime").timedelta(days=days)).isoformat()
    return store.select("apps", {
        "select": "id,name,owner,stars,category,first_seen,description,platforms,license",
        "first_seen": f"gte.{since}",
        "order": "first_seen.desc,stars.desc",
        "limit": limit,
    })


def log_run(store: Store, app_count: int, new_count: int, with_downloads: int,
            source: str = "manual") -> bool:
    try:
        store.insert("runs", [{
            "app_count": app_count,
            "new_count": new_count,
            "with_downloads": with_downloads,
            "source": source,
        }])
        return True
    except SupabaseError as e:
        print(f"  !! could not log run: {e}")
        return False


def push_catalog(store: Store, apps: list[dict], *, meta: dict | None = None,
                 source: str = "manual", verbose: bool = True) -> dict:
    """Upsert the whole catalog. first_seen is decided here, once, per app."""
    today = date.today().isoformat()
    known = fetch_first_seen(store, verbose=verbose)

    seen_today = 0
    rows = []
    for a in apps:
        prior = known.get(a["id"])
        if prior:
            a["firstSeen"] = prior                      # never rewritten
        else:
            a["firstSeen"] = a.get("firstSeen") or today
            if a["firstSeen"] == today:
                seen_today += 1
                # Whether an unseen row counts as "new" is decided by the
                # crawler, which knows if a real baseline exists. During a
                # seeding run nothing is ever new; otherwise trust the flag.
                if not (meta or {}).get("baseline", True):
                    a["isNew"] = False
                elif a.get("isNew") is None:
                    a["isNew"] = True
        rows.append(app_to_row(a))

    if verbose:
        print(f"  upserting {len(rows)} rows ({BATCH}/request)…")
    t0 = time.time()
    sent = store.upsert("apps", rows)
    if verbose:
        label = "new today" if (meta or {}).get("baseline", True) else \
                "dated today (baseline)"
        print(f"  wrote {sent} rows in {time.time() - t0:.1f}s "
              f"· {seen_today} {label}")

    new_count = (meta or {}).get("newToday", seen_today)
    log_run(store, len(apps), new_count,
            (meta or {}).get("withDownloads", 0), source)
    return {"pushed": sent, "first_seen_today": seen_today, "known_before": len(known)}


def check(verbose: bool = True) -> tuple[bool, list[str]]:
    """Probe the real endpoints. Returns (ok, problems)."""
    problems: list[str] = []
    envcfg.load_dotenv()
    url = envcfg.normalize_url(envcfg.get("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"))
    if not url:
        return False, ["SUPABASE_URL is not set (put it in .env)"]
    if verbose:
        print(f"  URL: {url}")

    store = connect()
    if not store:
        return False, ["no Supabase key set (SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY)"]

    # 1. is the project reachable at all?
    try:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/rest/v1/",
            headers={"apikey": store.key, "Authorization": f"Bearer {store.key}",
                     "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            if verbose:
                print(f"  ✓ REST endpoint reachable (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        # PostgREST answers 404 with {"message":"Invalid path specified..."} on a
        # freshly created project that has no tables yet. The server *did* answer,
        # so the URL and keys are fine — the schema just has not been applied.
        if e.code == 404:
            # PostgREST serves an OpenAPI listing at /rest/v1/ once it knows
            # about at least one table. A 404 here means it knows about none:
            # the schema was never applied (or the whole script rolled back).
            if verbose:
                print("  · REST endpoint reachable (HTTP 404 — it sees no tables)")
        elif e.code in (401, 403):
            problems.append(
                f"key rejected (HTTP {e.code}) — re-copy SUPABASE_ANON_KEY / "
                f"SUPABASE_SERVICE_KEY from Project Settings > API")
        else:
            problems.append(f"REST endpoint returned HTTP {e.code} — check {url}")
    except Exception as e:
        problems.append(f"cannot reach {url}: {e}")

    # 2. does the schema exist / is it readable?
    try:
        rows = store.select("apps", {"select": "id,first_seen", "limit": 1})
        if verbose:
            print(f"  ✓ table public.apps readable ({len(rows)} row sampled)")
    except SupabaseError as e:
        msg = str(e)
        if "404" in msg or "42P01" in msg:
            problems.append(
                "table public.apps does not exist — Supabase sees no tables in "
                "this project")
            ref = ""
            try:
                host = url.split("//", 1)[-1].split("/")[0]
                ref = host.split(".")[0]
            except Exception:
                pass
            if ref and verbose:
                print("  -> run the SQL here: "
                      "https://supabase.com/dashboard/project/"
                      f"{ref}/sql/new")
                print(f"  -> check that project really is '{ref}' "
                      "(the one your .env points at)")
        elif "401" in msg or "403" in msg:
            problems.append("key rejected — check SUPABASE_ANON_KEY / SERVICE_KEY")
        else:
            problems.append(f"cannot read public.apps: {msg}")

    # 3. can we write? (only meaningful with the service key)
    if envcfg.has_write_credentials():
        # log_run() reports failure by return value, so check the bool — a dead
        # write must never print a tick.
        if log_run(store, 0, 0, 0, source="check_setup"):
            if verbose:
                print("  ✓ write access confirmed (service key)")
        else:
            problems.append(
                "write test failed — the runs table rejected an insert; check "
                "SUPABASE_SERVICE_KEY and that schema.sql ran")
    elif verbose:
        print("  · anon key only — read-only check (writes need SUPABASE_SERVICE_KEY)")

    return (not problems), problems


# --------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="Supabase storage for SourceShelf")
    ap.add_argument("--check", action="store_true", help="verify credentials + schema")
    ap.add_argument("--push", action="store_true", help="push data/apps.json to Supabase")
    ap.add_argument("--stats", action="store_true", help="show stored row counts")
    ap.add_argument("--new", type=int, default=0, help="list arrivals from the last N days")
    args = ap.parse_args()

    if args.check or not (args.push or args.stats or args.new):
        print("supabase: checking…")
        ok, problems = check()
        if ok:
            print("supabase: OK ✓")
            return 0
        print("supabase: NOT READY ✗")
        for p in problems:
            print(f"  - {p}")
        return 1

    store = connect(require_write=args.push)
    if not store:
        print("supabase: not configured — set SUPABASE_URL and a key in .env")
        return 1

    if args.push:
        path = DATA / "apps.json"
        if not path.exists():
            print("no data/apps.json — run scripts/fetch_apps.py first")
            return 1
        payload = json.loads(path.read_text(encoding="utf-8"))
        print(f"pushing {len(payload.get('apps', []))} apps…")
        res = push_catalog(store, payload["apps"], meta=payload.get("meta"),
                           source="cli")
        print(f"done: {res}")
        # keep the local file in sync with first_seen assigned by the database
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        return 0

    if args.stats:
        for t in ("apps", "runs"):
            try:
                print(f"  {t}: {len(store.select(t, {'select': 'id', 'limit': 1000}, paginate=True))} rows")
            except SupabaseError as e:
                print(f"  {t}: {e}")
        return 0

    if args.new:
        rows = fetch_new_arrivals(store, days=args.new)
        for r in rows:
            print(f"  {r['first_seen']}  {r['stars']:>7}  {r['id']}")
        print(f"{len(rows)} arrivals in the last {args.new} days")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
