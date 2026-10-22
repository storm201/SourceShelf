#!/usr/bin/env python3
"""Spot-check the classifier: dump the catalog by category and flag entries
that look misplaced, so you know which OVERRIDES to add in taxonomy.py."""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from taxonomy import OVERRIDES  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", help="only show this category")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--suspicious", action="store_true",
                    help="only show low-confidence assignments")
    a = ap.parse_args()

    data = json.loads((ROOT / "data/apps.json").read_text(encoding="utf-8"))
    apps = data["apps"]
    meta = data.get("meta", {})

    by = defaultdict(list)
    for x in apps:
        by[x["category"]].append(x)
    for k in by:
        by[k].sort(key=lambda x: -x["stars"])

    print(f"{len(apps)} apps | generated {meta.get('generatedAt','?')} "
          f"| {meta.get('withDownloads',0)} with direct downloads\n")
    print(f"{'category':<26} {'apps':>5}")
    print("-" * 34)
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"{k:<26} {len(v):>5}")

    plats = Counter(p for x in apps for p in x["platforms"])
    print("\nplatforms:", ", ".join(f"{p}={n}" for p, n in plats.most_common()))
    lic = Counter(x["license"] or "none" for x in apps)
    print("licenses :", ", ".join(f"{p}={n}" for p, n in lic.most_common(10)))
    no_plat = [x for x in apps if not x["platforms"]]
    print(f"no platform detected: {len(no_plat)}")

    cats = [a.cat] if a.cat else sorted(by)
    for c in cats:
        rows = by.get(c, [])
        if a.suspicious:
            rows = [x for x in rows if x.get("confidence", 1) < 0.5 and x["id"] not in OVERRIDES]
        if not rows:
            continue
        print(f"\n### {c}  ({len(by.get(c, []))} total)")
        for x in rows[: a.limit]:
            flag = "  " if x["id"] in OVERRIDES else ("~~" if x.get("confidence", 1) < 0.5 else "  ")
            print(f" {flag}{x['stars']:>7} {x['id'][:46]:<46} "
                  f"{','.join(x['platforms'])[:38]:<38} {x['license'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
