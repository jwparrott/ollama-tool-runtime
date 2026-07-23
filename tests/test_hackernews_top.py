from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools.custom.hackernews_top import TOOL_SPEC, run


class HackerNewsTopTests(unittest.TestCase):
    def _mock_resp(self, payload: str):
        resp = MagicMock()
        resp.read.return_value = payload.encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "hackernews_top")

    def test_success(self) -> None:
        top_ids = self._mock_resp("[1001,1002]")
        story_1 = self._mock_resp(
            '{"id":1001,"type":"story","title":"Story A","url":"https://example.com/a",'
            '"by":"alice","score":123,"descendants":44,"time":1721700000}'
        )
        story_2 = self._mock_resp(
            '{"id":1002,"type":"story","title":"Story B","url":"https://example.com/b",'
            '"by":"bob","score":99,"descendants":20,"time":1721700500}'
        )
        with patch("urllib.request.urlopen", side_effect=[top_ids, story_1, story_2]):
            result = run({"limit": 2}, {})
        self.assertEqual(result["result_count"], 2)
        self.assertEqual(result["stories"][0]["id"], 1001)
        self.assertIn("created_utc", result["stories"][0])

    def test_non_list_topstories(self) -> None:
        with patch("urllib.request.urlopen", return_value=self._mock_resp('{"oops":true}')):
            result = run({"limit": 3}, {})
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
