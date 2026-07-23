from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools.custom.wikipedia_search import TOOL_SPEC, run


class WikipediaSearchTests(unittest.TestCase):
    def _mock_resp(self, payload: str):
        resp = MagicMock()
        resp.read.return_value = payload.encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "wikipedia_search")

    def test_empty_query(self) -> None:
        result = run({"query": "   "}, {})
        self.assertIn("error", result)

    def test_invalid_language(self) -> None:
        result = run({"query": "python", "language": "en-US"}, {})
        self.assertIn("error", result)

    def test_success(self) -> None:
        payload = (
            '{"query":{"search":[{"title":"Python (programming language)",'
            '"pageid":23862,"snippet":"<span>High-level</span> language"}]}}'
        )
        with patch("urllib.request.urlopen", return_value=self._mock_resp(payload)):
            result = run({"query": "python", "limit": 1, "language": "en"}, {})
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["pageid"], 23862)
        self.assertEqual(result["results"][0]["snippet"], "High-level language")
        self.assertIn("wikipedia.org/wiki/", result["results"][0]["url"])


if __name__ == "__main__":
    unittest.main()
