from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.custom.web_data_pipeline import TOOL_SPEC, run


class WebDataPipelineTests(unittest.TestCase):
    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "web_data_pipeline")

    def test_invalid_action(self) -> None:
        result = run({"action": "x"}, {})
        self.assertIn("error", result)

    def test_search_delegates(self) -> None:
        with patch("tools.custom.web_search.run", return_value={"ok": True, "result_count": 1, "results": []}) as mock_run:
            result = run({"action": "search", "query": "hello"}, {})
        self.assertEqual(result["action"], "search")
        self.assertTrue(result["ok"])
        mock_run.assert_called_once()

    def test_fetch_delegates(self) -> None:
        with patch("tools.custom.fetch_url.run", return_value={"ok": True, "content": "abc"}) as mock_run:
            result = run({"action": "fetch", "url": "https://example.com"}, {})
        self.assertEqual(result["action"], "fetch")
        self.assertTrue(result["ok"])
        mock_run.assert_called_once()

    def test_scrape_delegates(self) -> None:
        with patch("tools.custom.firecrawl_client.run", return_value={"ok": True, "response": {"x": 1}}) as mock_run:
            result = run({"action": "scrape", "url": "https://example.com", "api_key": "k"}, {})
        self.assertEqual(result["action"], "scrape")
        self.assertTrue(result["ok"])
        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
