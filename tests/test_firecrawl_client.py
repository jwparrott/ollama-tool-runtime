from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from tools.custom.firecrawl_client import TOOL_SPEC, run


class FirecrawlClientTests(unittest.TestCase):
    def _mock_response(self, payload: dict):
        resp = MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "firecrawl_client")

    def test_requires_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = run({"action": "scrape", "url": "https://example.com"}, {})
        self.assertIn("error", result)

    def test_invalid_url_scheme(self) -> None:
        result = run({"action": "scrape", "url": "file:///x", "api_key": "k"}, {})
        self.assertIn("error", result)

    def test_scrape_success(self) -> None:
        with patch("urllib.request.urlopen", return_value=self._mock_response({"success": True, "data": {"markdown": "# hi"}})):
            result = run(
                {
                    "action": "scrape",
                    "url": "https://example.com",
                    "api_key": "k",
                    "formats": ["markdown"],
                },
                {},
            )
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("action"), "scrape")

    def test_crawl_payload_success(self) -> None:
        with patch("urllib.request.urlopen", return_value=self._mock_response({"success": True, "id": "job1"})):
            result = run(
                {
                    "action": "crawl",
                    "url": "https://example.com",
                    "api_key": "k",
                    "limit": 5,
                    "max_depth": 2,
                    "include_paths": ["/docs/*"],
                    "exclude_paths": ["/admin/*"],
                },
                {},
            )
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("action"), "crawl")


if __name__ == "__main__":
    unittest.main()
