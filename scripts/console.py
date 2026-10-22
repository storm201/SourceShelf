"""Windows-safe console output.

Windows terminals default to a legacy code page (cp1252 / cp437), which raises
UnicodeEncodeError as soon as a script prints a non-ASCII character such as
"·", "→" or "✓". That kills the run with a traceback even though nothing is
actually wrong.

`safe_console()` switches stdout/stderr to errors="replace" so unsupported
characters degrade to "?" instead of crashing the process. On macOS/Linux it
is a no-op.
"""

from __future__ import annotations

import sys


def safe_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            # Stream is wrapped or already closed — nothing to do.
            pass
