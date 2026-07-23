"""Tests for the fetch_url custom tool."""

from __future__ import annotations

import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.fetch_url import run, TOOL_SPEC, _html_to_text


class FetchUrlSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "fetch_url")
        self.assertEqual(TOOL_SPEC["parameters"]["required"], ["url"])


class FetchUrlValidationTests(unittest.TestCase):
    def test_non_http_scheme_rejected(self):
        result = run({"url": "ftp://example.com"}, {})
        self.assertIn("error", result)

    def test_file_scheme_rejected(self):
        result = run({"url": "file:///etc/passwd"}, {})
        self.assertIn("error", result)

    def test_empty_url_rejected(self):
        result = run({"url": "   "}, {})
        self.assertIn("error", result)


class FetchUrlHttpTests(unittest.TestCase):
    def _mock_response(self, body: bytes, content_type: str = "text/html; charset=utf-8"):
        resp = MagicMock()
        resp.headers.get.return_value = content_type
        resp.read.return_value = body
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_successful_text_fetch(self):
        html_body = b"<html><body><p>Hello world</p></body></html>"
        with patch("urllib.request.urlopen", return_value=self._mock_response(html_body)):
            result = run({"url": "https://example.com"}, {})
        self.assertNotIn("error", result)
        self.assertIn("Hello world", result["content"])
        self.assertEqual(result["url"], "https://example.com")

    def test_html_stripped_by_default(self):
        html_body = b"<html><head><style>body{color:red}</style></head><body><p>Clean text</p></body></html>"
        with patch("urllib.request.urlopen", return_value=self._mock_response(html_body)):
            result = run({"url": "https://example.com"}, {})
        self.assertNotIn("<p>", result["content"])
        self.assertNotIn("color:red", result["content"])
        self.assertIn("Clean text", result["content"])

    def test_raw_returns_html(self):
        html_body = b"<html><body><p>Raw HTML</p></body></html>"
        with patch("urllib.request.urlopen", return_value=self._mock_response(html_body)):
            result = run({"url": "https://example.com", "raw": True}, {})
        self.assertIn("<p>", result["content"])

    def test_max_chars_truncates(self):
        body = b"x" * 10_000
        with patch("urllib.request.urlopen", return_value=self._mock_response(body, "text/plain")):
            result = run({"url": "https://example.com", "max_chars": 100}, {})
        self.assertEqual(len(result["content"]), 100)
        self.assertTrue(result["has_more"])

    def test_pagination_start_index(self):
        body = b"abcdefghij"
        with patch("urllib.request.urlopen", return_value=self._mock_response(body, "text/plain")):
            result = run({"url": "https://example.com", "start_index": 5, "max_chars": 3}, {})
        self.assertEqual(result["content"], "fgh")

    def test_http_error_returns_error(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
                "https://example.com", 404, "Not Found", {}, None)):
            result = run({"url": "https://example.com"}, {})
        self.assertIn("error", result)
        self.assertIn("404", result["error"])

    def test_url_error_returns_error(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            result = run({"url": "https://example.com"}, {})
        self.assertIn("error", result)

    def test_timeout_returns_error(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            result = run({"url": "https://example.com"}, {})
        self.assertIn("error", result)
        self.assertIn("timed out", result["error"])

    def test_has_more_false_when_content_fits(self):
        body = b"short content"
        with patch("urllib.request.urlopen", return_value=self._mock_response(body, "text/plain")):
            result = run({"url": "https://example.com"}, {})
        self.assertFalse(result["has_more"])
        self.assertIsNone(result["next_start_index"])


class HtmlToTextTests(unittest.TestCase):
    def test_strips_tags(self):
        self.assertEqual(_html_to_text("<p>hello</p>").strip(), "hello")

    def test_removes_script(self):
        result = _html_to_text("<script>alert('xss')</script>content")
        self.assertNotIn("alert", result)
        self.assertIn("content", result)

    def test_removes_style(self):
        result = _html_to_text("<style>.a{color:red}</style>text")
        self.assertNotIn("color", result)

    def test_decodes_entities(self):
        result = _html_to_text("&amp; &lt; &gt; &quot;")
        self.assertIn("&", result)
        self.assertIn("<", result)


if __name__ == "__main__":
    unittest.main()
