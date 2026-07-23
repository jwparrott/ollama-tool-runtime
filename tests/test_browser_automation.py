from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.custom.browser_automation import TOOL_SPEC, run


class BrowserAutomationTests(unittest.TestCase):
    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "browser_automation")

    def test_invalid_scheme(self) -> None:
        result = run({"url": "file:///tmp/x"}, {})
        self.assertIn("error", result)

    def test_auto_fallback_to_selenium(self) -> None:
        with patch("tools.custom.browser_automation._run_playwright", return_value={"error": "pw fail"}):
            with patch(
                "tools.custom.browser_automation._run_selenium",
                return_value={"ok": True, "title": "t", "url": "https://x", "content": "c", "truncated": False},
            ):
                result = run({"url": "https://example.com", "backend": "auto"}, {})
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("backend"), "selenium")

    def test_playwright_success(self) -> None:
        with patch(
            "tools.custom.browser_automation._run_playwright",
            return_value={"ok": True, "title": "ok", "url": "https://e", "content": "x", "truncated": False},
        ):
            result = run({"url": "https://example.com", "backend": "playwright"}, {})
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("backend"), "playwright")


if __name__ == "__main__":
    unittest.main()
