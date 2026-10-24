#!/usr/bin/env python3
"""
Unit tests for build_single.py, including README dynamic stats update.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_single import update_readme


class TestUpdateReadme(unittest.TestCase):
    def test_update_initial_readme_without_markers(self):
        initial_content = (
            "# 📡 SourceShelf\n\n"
            "> **Current catalog: 1,619 apps · 23 categories · 10 platforms · 276 with direct\n"
            "> download links**, crawled live from the GitHub API.\n"
            ">\n"
            "> ▶️ **Just want the commands? → [RUN.md](RUN.md)**\n\n"
            "- **Seeding run claims nothing.** Otherwise day one would announce \"1,619 new apps today\", which is noise.\n"
        )
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(initial_content)
            temp_path = Path(tf.name)

        try:
            meta = {
                "count": 1850,
                "categories": ["cat1", "cat2"],
                "platforms": ["plat1", "plat2", "plat3"],
                "withDownloads": 820,
            }
            changed = update_readme(meta, readme_path=temp_path)
            self.assertTrue(changed)

            updated = temp_path.read_text(encoding="utf-8")
            self.assertIn("<!-- CATALOG_STATS_START -->", updated)
            self.assertIn("<!-- CATALOG_STATS_END -->", updated)
            self.assertIn("1,850 apps · 2 categories · 3 platforms · 820 with direct", updated)
            self.assertIn("catalog-1%2C850%20apps-blue", updated)
            self.assertIn("Otherwise day one would announce \"1,850 new apps today\"", updated)

            # Idempotent: running again with same data should return False
            changed_again = update_readme(meta, readme_path=temp_path)
            self.assertFalse(changed_again)

            # Updating with new count
            meta["count"] = 2000
            meta["withDownloads"] = 900
            changed_third = update_readme(meta, readme_path=temp_path)
            self.assertTrue(changed_third)

            updated_third = temp_path.read_text(encoding="utf-8")
            self.assertIn("2,000 apps · 2 categories · 3 platforms · 900 with direct", updated_third)
            self.assertIn("catalog-2%2C000%20apps-blue", updated_third)
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
