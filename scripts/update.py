#!/usr/bin/env python3
"""
One-shot local updater: crawl GitHub, then rebuild sourceshelf.html.

    python3 scripts/update.py                 # normal daily update
    python3 scripts/update.py --quick         # skip download-link resolution (fast)
    python3 scripts/update.py --min-stars 1000
    python3 scripts/update.py --no-token      # force the no-quota web fallback

Set GITHUB_TOKEN in your environment for a much larger API budget:
    export GITHUB_TOKEN=ghp_xxx      # macOS / Linux
    set GITHUB_TOKEN=ghp_xxx         # Windows cmd
    $env:GITHUB_TOKEN="ghp_xxx"      # Windows PowerShell

A token needs NO scopes/permissions for public data — a classic PAT with every
checkbox unticked is enough.
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover - never fatal
    pass


import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd: list[str], label: str) -> bool:
    print(f"\n=== {label} ===", flush=True)
    t0 = time.time()
    try:
        subprocess.run(cmd, cwd=ROOT, check=True)
    except subprocess.CalledProcessError as e:
        print(f"!! {label} failed (exit {e.returncode})", flush=True)
        return False
    print(f"--- {label} finished in {time.time() - t0:.1f}s", flush=True)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-stars", type=int, default=400)
    ap.add_argument("--releases", type=int, default=-1,
                    help="repos to resolve download links for (-1 = auto)")
    ap.add_argument("--quick", action="store_true",
                    help="don't resolve download links (much faster)")
    ap.add_argument("--no-token", action="store_true",
                    help="pretend there is no token (public web pages only)")
    ap.add_argument("--force", action="store_true",
                    help="ignore the 20h search cache and re-query GitHub")
    args = ap.parse_args()

    has_token = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    if args.no_token:
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.pop("GH_TOKEN", None)
        has_token = False
    elif not has_token:
        # make it obvious how to speed this up
        print("note: no GITHUB_TOKEN set — using the public web fallback for "
              "download links (slower, but no quota needed).")

    print(f"SourceShelf local update | python {sys.version.split()[0]} | "
          f"token={'yes' if has_token else 'no'}")

    crawl = [PY, "scripts/fetch_apps.py", "--min-stars", str(args.min_stars)]
    if args.quick:
        crawl += ["--releases", "0"]
    else:
        crawl += ["--releases", str(args.releases)]
    if args.force:
        crawl.append("--force")

    if not run(crawl, "1/2 crawling GitHub"):
        print("\nThe catalog was NOT rebuilt (data is unchanged).", flush=True)
        return 1
    if not run([PY, "scripts/build_single.py"], "2/2 building sourceshelf.html"):
        return 1

    import json
    meta = json.loads((ROOT / "data" / "apps.json").read_text(encoding="utf-8"))["meta"]
    print("\n" + "=" * 58)
    print(f"  {meta['count']:,} apps  ·  {len(meta['categories'])} categories  ·  "
          f"{meta.get('withDownloads', 0)} with direct downloads")
    if meta.get("seedRun"):
        print("  seeded — new arrivals appear from the next run")
    elif meta.get("newToday"):
        print(f"  +{meta['newToday']} new since the last update")
    else:
        print("  no new apps since the last update")
    src = meta.get("historySource", "none")
    print(f"  history: {src}" + ("" if src == "supabase"
          else "  (set SUPABASE_URL in .env to keep history across machines)"))
    print(f"  built at {meta['generatedAt']}")
    print("  open:     sourceshelf.html    (double-click it)")
    print("  or serve: python3 scripts/serve.py")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
