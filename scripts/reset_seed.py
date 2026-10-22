#!/usr/bin/env python3
"""Reset data/apps.json to a clean baseline.

Why this exists: "new arrivals" is computed by comparing each app's
`firstSeen` against the previous run. If the shipped dataset already contains
discovery dates from testing, or from a different machine, the first real run
will announce a bogus batch of "new" apps.

After running this, every app is stamped with today's date, nothing is flagged
new, and the New arrivals section stays empty until the *next* crawl finds
something genuinely unseen.

    python3 scripts/reset_seed.py            # reset to a clean baseline
    python3 scripts/reset_seed.py --dry-run  # show what would change

This does NOT touch Supabase. To reset history there too, delete the rows in
the dashboard (Table Editor > apps > select all > delete), or run:
    truncate table public.apps;
"""

from __future__ import annotations

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> int:
    ap = argparse.ArgumentParser(description="Reset data/apps.json to a clean baseline")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = DATA / "apps.json"
    if not path.exists():
        print(f"no {path} — nothing to reset")
        return 1

    doc = json.loads(path.read_text(encoding="utf-8"))
    apps = doc.get("apps") or []
    meta = doc.get("meta") or {}
    today = datetime.now(timezone.utc).date().isoformat()

    before = {
        "baselineDate": meta.get("baselineDate"),
        "newToday": meta.get("newToday"),
        "isNew": sum(1 for a in apps if a.get("isNew")),
        "arrivals": len(meta.get("newArrivals") or []),
    }

    for a in apps:
        a["firstSeen"] = today
        a["isNew"] = False
        a.pop("starsDelta", None)

    meta.update({
        "baselineDate": today,
        "baseline": False,
        "seedRun": True,
        "newToday": 0,
        "newArrivals": [],
        "previousCount": len(apps),
        "historySource": "local",
    })
    meta.pop("supabase", None)
    meta.pop("supabaseError", None)
    doc["meta"] = meta

    after = {
        "baselineDate": meta["baselineDate"],
        "newToday": meta["newToday"],
        "isNew": 0,
        "arrivals": 0,
    }

    if args.dry_run:
        print(f"would reset {len(apps):,} apps")
        print(f"  before: {before}")
        print(f"  after:  {after}")
        return 0

    path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    (DATA / "apps.js").write_text(
        "window.__SOURCESHELF__=" + json.dumps(doc, separators=(",", ":")) + ";",
        encoding="utf-8")

    print(f"reset {len(apps):,} apps to a clean baseline ({today})")
    print(f"  before: {before}")
    print(f"  after:  {after}")
    print("\nnext: python3 scripts/build_single.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
