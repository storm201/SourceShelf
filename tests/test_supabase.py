#!/usr/bin/env python3
"""
End-to-end test of the Supabase storage layer against a local mock of
PostgREST. No network, no account, no dependencies:

    python3 tests/test_supabase.py

Proves the crawler→Supabase contract: correct endpoint paths, auth headers,
upsert params, batching, pagination, first_seen preservation, retry on 503,
and that a failure is reported without exploding.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import mock_supabase  # noqa: E402
import supabase_store as S  # noqa: E402

PASS, FAIL = "\033[32m✓\033[0m", "\033[31m✗\033[0m"
fails: list[str] = []


def ok(cond: bool, name: str, detail: str = "") -> None:
    print(f"  {PASS if cond else FAIL} {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        fails.append(name)


def sample_apps(n: int = 520) -> list[dict]:
    """n apps so we cross the 250-row batch boundary twice."""
    out = []
    for i in range(n):
        out.append({
            "id": f"owner{i}/app{i}",
            "name": f"app{i}",
            "owner": f"owner{i}",
            "url": f"https://github.com/owner{i}/app{i}",
            "description": f"Test app number {i}",
            "stars": 1000 + i,
            "forks": i,
            "language": "Python",
            "license": "MIT",
            "category": "Developer Tools",
            "platforms": ["Linux", "Windows"],
            "topics": ["cli", "test"],
            "createdAt": "2024-01-01",
            "pushedAt": "2026-10-01",
            "release": {"tag": "v1.0.0", "assets": [{"name": "x.exe", "size": 10,
                                                     "url": "u", "os": ["windows"],
                                                     "downloads": 0}],
                        "page": "https://github.com/owner0/app0/releases/tag/v1.0.0"},
        })
    return out


def main() -> int:
    srv, url, state = mock_supabase.serve_in_background()
    print(f"\nmock Supabase at {url}\n")

    os.environ["SUPABASE_URL"] = url
    os.environ["SUPABASE_SERVICE_KEY"] = mock_supabase.KEY
    os.environ.pop("SUPABASE_ANON_KEY", None)

    print("connect + health")
    store = S.connect(require_write=True)
    ok(store is not None, "Store built from env")
    ok_health, problems = S.check(verbose=False)
    ok(ok_health, "check() passes against mock", "; ".join(problems) or "clean")

    print("\npush 520 apps (crosses the 250-row batch size)")
    apps = sample_apps(520)
    res = S.push_catalog(store, apps, meta={"newToday": 0, "withDownloads": 520},
                         source="test", verbose=False)
    ok(res["pushed"] == 520, "all 520 rows sent", f"pushed={res['pushed']}")
    ok(len(state.apps) == 520, "all rows stored", f"{len(state.apps)} in db")
    ok(len(state.runs) >= 1, "crawl logged to runs", f"{len(state.runs)} run rows")

    batches = [p for m, p, _ in state.requests if m == "POST" and "on_conflict" in p]
    ok(len(batches) >= 3, "batched into >=3 requests", f"{len(batches)} POSTs")
    hdrs = [h for m, p, h in state.requests if m == "POST" and "on_conflict" in p]
    ok(all("merge-duplicates" in h.get("Prefer", "") for h in hdrs),
       "upsert Prefer header set")
    def hget(h, name):
        # HTTP header names are case-insensitive; urllib title-cases them
        for k, v in h.items():
            if k.lower() == name.lower():
                return v
        return ""

    ok(all(hget(h, "apikey") == mock_supabase.KEY for h in hdrs),
       "apikey header sent")
    ok(all(hget(h, "authorization").startswith("Bearer ") for h in hdrs),
       "bearer auth header sent")
    ok(all(hget(h, "content-type") == "application/json" for h in hdrs),
       "content-type json")
    ok(all("on_conflict=id" in p for p in batches), "on_conflict=id in path")

    print("\nfirst_seen semantics")
    stored = state.apps["owner0/app0"]
    ok(isinstance(stored.get("first_seen"), str), "first_seen written",
       stored.get("first_seen"))
    ok(stored.get("release") is not None, "release jsonb stored")
    ok(stored.get("platforms") == ["Linux", "Windows"], "platforms stored as array")
    first_dates = {r["first_seen"] for r in state.apps.values()}
    ok(len(first_dates) == 1, "every seeded row shares one discovery date")

    # second run: pretend today is later and push again. first_seen must NOT move.
    print("\nsecond push must not rewrite history")
    before = dict(state.apps["owner0/app0"])
    old_date = before["first_seen"]
    state.apps["owner0/app0"]["first_seen"] = "2020-01-01"   # age it
    res2 = S.push_catalog(store, sample_apps(520), meta={"newToday": 0},
                          source="test", verbose=False)
    ok(res2["known_before"] >= 500, "history loaded from db",
       f"{res2['known_before']} known")
    ok(state.apps["owner0/app0"]["first_seen"] == "2020-01-01",
       "existing first_seen preserved", state.apps["owner0/app0"]["first_seen"])

    # a brand-new app should get today's date and count as first seen today
    print("\nnew app detection")
    extra = sample_apps(3)
    for a in extra:
        a["id"] = a["id"] + "-brandnew"
    res3 = S.push_catalog(store, extra, meta={"newToday": 0}, source="test",
                          verbose=False)
    ok(res3["first_seen_today"] == 3, "3 brand-new rows dated today",
       f"{res3['first_seen_today']}")

    print("\npagination (1000-row pages)")
    many = sample_apps(1200)
    for a in many:
        a["id"] = "pg/" + a["id"]
    S.push_catalog(store, many, meta={"newToday": 0}, source="test", verbose=False)
    hist = S.fetch_first_seen(store, verbose=False)
    ok(len(hist) >= 1700, "history read across pages", f"{len(hist)} ids")

    print("\nreads")
    rows = store.select("apps", {"select": "id,stars", "limit": 5,
                                 "order": "stars.desc"})
    ok(len(rows) == 5, "limit respected", f"{len(rows)} rows")
    ok(set(rows[0]) == {"id", "stars"}, "select projects columns")

    arrivals = S.fetch_new_arrivals(store, days=7, limit=50)
    ok(isinstance(arrivals, list) and len(arrivals) > 0, "new arrivals query works",
       f"{len(arrivals)} rows")

    print("\nresilience")
    state.fail_next = 1
    try:
        S.log_run(store, 1, 1, 1, source="retry-test")
        ok(True, "retries transparently on 503")
    except Exception as e:
        ok(False, "retries transparently on 503", str(e)[:80])

    # wrong key must fail loudly, not silently
    bad = S.Store(url, "wrong-key")
    try:
        bad.select("apps", {"select": "id", "limit": 1})
        ok(False, "bad key raises")
    except S.SupabaseError as e:
        ok("401" in str(e), "bad key raises SupabaseError", "HTTP 401")

    # missing table should be recognised as "run the schema"
    noschema = S.Store(url, mock_supabase.KEY)
    try:
        noschema.select("does_not_exist", {"select": "*"})
        ok(False, "missing table detected")
    except S.SupabaseError as e:
        ok("404" in str(e), "missing table detected", "HTTP 404")

    srv.shutdown()

    print("\n" + "=" * 58)
    if fails:
        print(f"\033[31m{len(fails)} FAILED:\033[0m " + ", ".join(fails))
        return 1
    print("\033[32mall Supabase layer tests passed\033[0m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
