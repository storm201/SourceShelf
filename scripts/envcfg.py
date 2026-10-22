"""
Tiny .env loader — no dependencies.

Reads KEY=VALUE lines from a .env file next to the project root and puts them in
os.environ (existing environment variables always win, so GitHub Actions secrets
are never overwritten by a stray local file).

Deliberately not a full dotenv implementation: no interpolation, no multiline.
That keeps "runs on my PC with no errors" true on a bare Python install.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None, override: bool = False) -> list[str]:
    """Load .env into os.environ. Returns the names that were set."""
    f = path or (ROOT / ".env")
    if not f.exists():
        return []
    loaded = []
    try:
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if key.startswith("export "):
                key = key[7:].strip()
            val = val.strip().strip('"').strip("'")
            if not key:
                continue
            if key in os.environ and not override:
                continue
            os.environ[key] = val
            loaded.append(key)
    except Exception as e:                                   # never fatal
        print(f"  (could not read {f.name}: {e})")
    return loaded


def get(*names: str, default: str = "") -> str:
    """First non-empty environment value among `names`."""
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return default


def normalize_url(url: str) -> str:
    """Return the bare project origin, e.g. https://abcdefgh.supabase.co

    Supabase's dashboard shows the *REST* URL (".../rest/v1/") with a Copy
    button, so it is easy to paste that by mistake. The client appends
    /rest/v1/ itself, so a pasted REST URL would request
    /rest/v1/rest/v1/apps and fail with:
        404 Invalid path specified in request URL
    Strip any API suffix so both forms work.
    """
    u = (url or "").strip().rstrip("/")
    for suffix in ("/rest/v1", "/rest", "/auth/v1", "/storage/v1"):
        if u.endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
    return u


def supabase_config(require_secret: bool = False) -> tuple[str, str] | None:
    """(url, key) or None. Prefers the service key, falls back to the anon key."""
    url = normalize_url(get("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"))
    if not url:
        return None
    key = get("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
              "SUPABASE_SECRET_KEY")
    if not key:
        if require_secret:
            return None
        key = get("SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
    return (url, key) if key else None


def has_write_credentials() -> bool:
    return bool(get("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL") and
                get("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
                    "SUPABASE_SECRET_KEY"))
