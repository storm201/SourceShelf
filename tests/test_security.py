#!/usr/bin/env python3
"""
Security validation tests for SourceShelf.
Tests:
  1. safeUrl() & escapeHtml() XSS / injection neutralization
  2. is_safe_download_url() download link validation
  3. build_single.py JWT role enforcement & secret scanning
  4. Content Security Policy headers / meta tags
  5. .gitignore coverage
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_apps import is_safe_download_url
from build_single import parse_jwt_role, check_build_secrets


class TestDownloadUrlSecurity(unittest.TestCase):
    def test_valid_github_download_urls(self):
        valid = [
            "https://github.com/torvalds/linux/releases/download/v1.0/kernel.tar.gz",
            "https://github.com/my-org/my_app/releases/download/v2.1.0-beta.1/App.dmg",
            "https://github.com/user/repo/releases/download/1.0/installer.exe",
        ]
        for url in valid:
            with self.subTest(url=url):
                repo = url.split("github.com/")[1].split("/releases/")[0]
                self.assertTrue(is_safe_download_url(url, repo))

    def test_rejects_subdomain_or_domain_spoofing(self):
        attacks = [
            ("https://github.com.evil.com/owner/repo/releases/download/v1/app.exe", "owner/repo"),
            ("https://evilgithub.com/owner/repo/releases/download/v1/app.exe", "owner/repo"),
            ("https://notgithub.com/owner/repo/releases/download/v1/app.exe", "owner/repo"),
            ("https://github.com@evil.com/owner/repo/releases/download/v1/app.exe", "owner/repo"),
        ]
        for url, repo in attacks:
            with self.subTest(url=url):
                self.assertFalse(is_safe_download_url(url, repo))

    def test_rejects_non_https_and_protocols(self):
        attacks = [
            ("http://github.com/owner/repo/releases/download/v1/app.exe", "owner/repo"),
            ("javascript:alert(1)", "owner/repo"),
            ("data:text/html,<script>alert(1)</script>", "owner/repo"),
            ("file:///etc/passwd", "owner/repo"),
        ]
        for url, repo in attacks:
            with self.subTest(url=url):
                self.assertFalse(is_safe_download_url(url, repo))

    def test_rejects_mismatched_repo_or_invalid_path(self):
        attacks = [
            ("https://github.com/other/other_repo/releases/download/v1/app.exe", "owner/repo"),
            ("https://github.com/owner/repo/issues", "owner/repo"),
            ("https://github.com/owner/repo/releases", "owner/repo"),
            ("https://github.com/owner/repo/raw/main/evil.exe", "owner/repo"),
        ]
        for url, repo in attacks:
            with self.subTest(url=url):
                self.assertFalse(is_safe_download_url(url, repo))


class TestJwtRoleValidation(unittest.TestCase):
    def _make_dummy_jwt(self, role: str) -> str:
        header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"role": role, "exp": 2000000000}).encode()).decode().rstrip("=")
        sig = "dummy_signature_value"
        return f"{header}.{payload}.{sig}"

    def test_parse_jwt_roles(self):
        anon_jwt = self._make_dummy_jwt("anon")
        service_jwt = self._make_dummy_jwt("service_role")
        admin_jwt = self._make_dummy_jwt("admin")

        self.assertEqual(parse_jwt_role(anon_jwt), "anon")
        self.assertEqual(parse_jwt_role(service_jwt), "service_role")
        self.assertEqual(parse_jwt_role(admin_jwt), "admin")

    def test_secret_scanner_detects_service_role_and_bad_jwt(self):
        # Current dist and sourceshelf.html should be clean
        self.assertTrue(check_build_secrets())

        # Test detection of service_role in a temp JS file in dist/
        test_file = ROOT / "dist" / "leak_test.js"
        try:
            test_file.write_text('const secret = "service_role";', encoding="utf-8")
            self.assertFalse(check_build_secrets())
        finally:
            if test_file.exists():
                test_file.unlink()

        # Test detection of non-anon JWT in a temp JS file in dist/
        bad_jwt = self._make_dummy_jwt("service_role")
        try:
            test_file.write_text(f'const token = "{bad_jwt}";', encoding="utf-8")
            self.assertFalse(check_build_secrets())
        finally:
            if test_file.exists():
                test_file.unlink()


class TestFrontendXSSAndUrlSanitization(unittest.TestCase):
    def test_frontend_escaping_and_safe_url_with_node(self):
        """Run Node.js to evaluate safeUrl and esc from assets/app.js against real attack payloads."""
        node_script = r"""
        const fs = require('fs');
        const lines = fs.readFileSync('assets/app.js', 'utf8').split(/\r?\n/);

        const escLine = lines.find(l => l.includes('const esc ='));
        if (!escLine) throw new Error('esc not found in app.js');

        const safeUrlStart = lines.findIndex(l => l.includes('const safeUrl ='));
        if (safeUrlStart === -1) throw new Error('safeUrl not found in app.js');
        const safeUrlLines = lines.slice(safeUrlStart, safeUrlStart + 10).join('\n');

        const bindFn = new Function('global', 'window', escLine + '\n' + safeUrlLines + '\nglobal.esc = esc; global.safeUrl = safeUrl;');
        bindFn(global, { location: { origin: 'https://sourceshelf.dev' } });

        // Test safeUrl
        const badUrls = [
            'javascript:alert(1)',
            'JaVaScRiPt:alert(document.cookie)',
            'data:text/html,<script>alert(1)</script>',
            'vbscript:msgbox(1)',
            'http://evil.com',
            'ftp://evil.com',
            'file:///etc/passwd',
            'javascript://evil.com%0Aalert(1)'
        ];
        for (const u of badUrls) {
            const res = safeUrl(u);
            if (res !== '#') {
                console.error(`safeUrl FAILED on ${u}: got ${res}`);
                process.exit(1);
            }
        }

        const goodUrls = [
            'https://github.com/foo/bar',
            'https://example.com/download.zip',
            'https://sub.domain.org/path?a=1&b=2#frag'
        ];
        for (const u of goodUrls) {
            const res = safeUrl(u);
            if (res !== esc(u)) {
                console.error(`safeUrl FAILED to preserve valid url ${u}: got ${res}`);
                process.exit(1);
            }
        }

        // Test esc
        const xssPayloads = [
            '<script>alert("xss")</script>',
            '"><img src=x onerror=alert(1)>',
            "foo ' onmouseover='alert(1)'",
            '& < > " \''
        ];
        for (const p of xssPayloads) {
            const escaped = esc(p);
            if (escaped.includes('<') || escaped.includes('>') || escaped.includes('"') || escaped.includes("'")) {
                console.error(`esc FAILED on ${p}: got ${escaped}`);
                process.exit(1);
            }
        }

        console.log("ALL_JS_SANITIZATIONS_PASS");
        """
        res = subprocess.run(
            ["node", "-"],
            input=node_script,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Node script failed:\n{res.stderr}\n{res.stdout}")
        self.assertIn("ALL_JS_SANITIZATIONS_PASS", res.stdout)


class TestCspAndRepoHardening(unittest.TestCase):
    def test_csp_meta_tag_present(self):
        index_html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('http-equiv="Content-Security-Policy"', index_html)
        self.assertIn("default-src 'self'", index_html)
        self.assertIn("base-uri 'none'", index_html)
        self.assertIn("form-action 'none'", index_html)
        self.assertIn("https://avatars.githubusercontent.com", index_html)

    def test_gitignore_covers_sensitive_files(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env", gitignore)
        self.assertIn(".env.*", gitignore)
        self.assertIn("!.env.example", gitignore)
        self.assertIn("dist/", gitignore)


if __name__ == "__main__":
    unittest.main()
