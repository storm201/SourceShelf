#!/usr/bin/env python3
"""
Approve an app suggestion from a GitHub Issue or CLI, and save it to data/community_apps.json.

Usage:
    # From GitHub Actions environment:
    python scripts/approve_suggestion.py

    # From CLI directly:
    python scripts/approve_suggestion.py --repo "zed-industries/zed" --category "Developer Tools"
"""

# Windows consoles default to a legacy code page; keep non-ASCII output from crashing.
try:
    from console import safe_console
    safe_console()
except Exception:  # pragma: no cover
    pass

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMUNITY_FILE = ROOT / "data" / "community_apps.json"

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from taxonomy import CATEGORY_RULES, PLATFORM_RULES
    VALID_CATEGORIES = list(CATEGORY_RULES.keys())
    VALID_PLATFORMS = list(PLATFORM_RULES.keys())
except Exception:
    VALID_CATEGORIES = [
        "AI & LLM", "Developer Tools", "Privacy & Security", "Notes & Knowledge",
        "Productivity", "Media & Audio", "Video & Streaming", "Photos & Design",
        "Files & Sync", "Communication", "Self-Hosting & Homelab", "Automation",
        "Networking", "System & Utilities", "Reading & Books", "Health & Fitness",
        "Finance", "Education", "Gaming & Emulation", "Download & Torrent",
        "Maps & Travel", "Monitoring & Dashboards", "Other"
    ]
    VALID_PLATFORMS = [
        "Windows", "macOS", "Linux", "Android", "iOS", "Web", "Self-Hosted",
        "CLI / TUI", "Browser Extension", "VS Code"
    ]


def parse_repo_from_text(text: str) -> str | None:
    """Extract owner/repo from text or URLs."""
    if not text:
        return None
    # 1. Look for explicit repo URL in markdown
    m = re.search(r"github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", text, re.I)
    if m:
        repo = m.group(1).rstrip("/").rstrip(".")
        if repo.endswith(".git"):
            repo = repo[:-4]
        # Ignore our own repository if mentioned in footer
        if repo.lower() != "storm201/sourceshelf":
            return repo

    # 2. Look for owner/repo pattern under a heading
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if any(h in line.lower() for h in ("repository", "repo url", "repo:")):
            for next_line in lines[i + 1: i + 4]:
                stripped = next_line.strip().strip("`").strip("<>").strip()
                m2 = re.search(r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", stripped)
                if m2:
                    repo = m2.group(1).rstrip("/").rstrip(".")
                    if repo.endswith(".git"):
                        repo = repo[:-4]
                    if repo.lower() != "storm201/sourceshelf":
                        return repo

    # 3. Direct string pattern
    m3 = re.search(r"\b([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)\b", text)
    if m3:
        repo = m3.group(1).rstrip("/").rstrip(".")
        if repo.endswith(".git"):
            repo = repo[:-4]
        if repo.lower() != "storm201/sourceshelf":
            return repo

    return None


def parse_category_from_text(text: str) -> str:
    """Extract category from issue text, matching against standard categories."""
    if not text:
        return "Other"

    # Search for Category section
    cat_match = re.search(r"###\s*(?:Primary\s*)?Category\s*\n+([^\n#]+)", text, re.I)
    candidate = cat_match.group(1).strip() if cat_match else ""

    if not candidate:
        # Check if any category name is explicitly present in text
        for cat in VALID_CATEGORIES:
            if re.search(rf"\b{re.escape(cat)}\b", text, re.I):
                return cat
        return "Other"

    # Match candidate against known categories
    for cat in VALID_CATEGORIES:
        if candidate.lower() == cat.lower():
            return cat
    return "Other"


def parse_platforms_from_text(text: str) -> list[str]:
    """Extract checked platforms from issue checkboxes."""
    if not text:
        return []
    platforms = []
    # Match GitHub checkboxes: - [x] Platform
    for m in re.finditer(r"-\s*\[[xX]\]\s*([a-zA-Z0-9 /+-]+)", text):
        val = m.group(1).strip()
        for p in VALID_PLATFORMS:
            if val.lower() == p.lower():
                platforms.append(p)
                break
    return platforms


def add_to_community_catalog(repo: str, category: str, platforms: list[str]) -> bool:
    """Save the approved app to data/community_apps.json."""
    data = {}
    if COMMUNITY_FILE.exists():
        try:
            data = json.loads(COMMUNITY_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data[repo] = {
        "category": category,
        "platforms": platforms,
        "approvedAt": datetime.now(timezone.utc).isoformat(),
    }

    COMMUNITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMUNITY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Approve and register an app suggestion.")
    ap.add_argument("--repo", help="Repository in owner/repo format")
    ap.add_argument("--category", help="Category name")
    ap.add_argument("--platforms", help="Comma-separated platform names")
    ap.add_argument("--body", help="Raw issue body text")
    args = ap.parse_args()

    body = args.body or os.environ.get("ISSUE_BODY", "")
    title = os.environ.get("ISSUE_TITLE", "")
    full_text = f"{title}\n\n{body}"

    repo = args.repo or parse_repo_from_text(full_text)
    if not repo or "/" not in repo:
        print(f"ERROR: Could not parse repository name from input:\n{full_text[:300]}", file=sys.stderr)
        return 1

    category = args.category or parse_category_from_text(full_text)
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    else:
        platforms = parse_platforms_from_text(full_text)

    add_to_community_catalog(repo, category, platforms)
    print(f"SUCCESS: Approved {repo} -> Category: {category}, Platforms: {platforms}")

    # Set GitHub Actions output parameters if running in CI
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"repo={repo}\n")
            f.write(f"category={category}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
