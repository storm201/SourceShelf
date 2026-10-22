#!/usr/bin/env bash
# SourceShelf — local updater for macOS / Linux.
#   ./update.sh              normal update
#   ./update.sh --quick      skip download-link lookup (fast)
# Set a token for a much bigger API budget:  export GITHUB_TOKEN=ghp_xxx
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
[ -n "$PY" ] || { echo "Python 3 is required: https://www.python.org/downloads/"; exit 1; }

"$PY" scripts/update.py "$@"
