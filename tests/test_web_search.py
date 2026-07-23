"""Tests for the web_search custom tool."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make the tools package importable when tests run from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.web_search import run, TOOL_SPEC  # noqa: E402


class WebSearchSpecTests(unittest.TestCase):
    def test_spec_has_required_fields(self):
        self.assertEqual(TOOL_SPEC["name"], "web_search")
        self.assertIn("description", TOOL_SPEC)
        self.assertEqual(TOOL_SPEC["parameters"]["required"], ["query"])

    def test_spec_properties(self):
        props = TOOL_SPEC["parameters"]["properties"]
        self.assertIn("query", props)
        self.assertIn("max_results", props)
        self.assertIn("search_type", props)


class WebSearchValidationTests(unittest.TestCase):
    def test_empty_query_returns_error(self):
        result = run({"query": "   "}, {})
        self.assertIn("error", result)

    def test_invalid_search_type_defaults_to_text(self):
        fake_results = [{"title": "t", "href": "http://x.com", "body": "b"}]
        mock_ddgs = _make_mock_ddgs(text_results=fake_results)

        with _patch_ddgs(mock_ddgs):
            result = run({"query": "hello", "search_type": "invalid"}, {})

        self.assertEqual(result["search_type"], "text")
        mock_ddgs.text.assert_called_once()

    def test_max_results_clamped_to_10(self):
        fake_results = [{"title": "t", "href": "http://x.com", "body": "b"}]
        mock_ddgs = _make_mock_ddgs(text_results=fake_results)

        with _patch_ddgs(mock_ddgs):
            run({"query": "hello", "max_results": 999}, {})

        self.assertEqual(mock_ddgs.text.call_args[1]["max_results"], 10)

    def test_max_results_clamped_to_1(self):
        fake_results = [{"title": "t", "href": "http://x.com", "body": "b"}]
        mock_ddgs = _make_mock_ddgs(text_results=fake_results)

        with _patch_ddgs(mock_ddgs):
            run({"query": "hello", "max_results": -5}, {})

        self.assertEqual(mock_ddgs.text.call_args[1]["max_results"], 1)


class WebSearchResultTests(unittest.TestCase):
    def test_text_search_returns_structured_results(self):
        raw = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
        ]
        mock_ddgs = _make_mock_ddgs(text_results=raw)

        with _patch_ddgs(mock_ddgs):
            result = run({"query": "test query"}, {})

        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["search_type"], "text")
        self.assertEqual(result["result_count"], 2)
        self.assertEqual(result["results"][0]["title"], "Result 1")
        self.assertEqual(result["results"][0]["url"], "https://example.com/1")
        self.assertEqual(result["results"][0]["snippet"], "Snippet 1")

    def test_news_search_returns_structured_results(self):
        raw = [
            {
                "title": "News 1",
                "url": "https://news.example.com/1",
                "body": "News snippet",
                "source": "Example News",
                "date": "2025-07-23",
            }
        ]
        mock_ddgs = _make_mock_ddgs(news_results=raw)

        with _patch_ddgs(mock_ddgs):
            result = run({"query": "breaking news", "search_type": "news"}, {})

        self.assertEqual(result["search_type"], "news")
        self.assertEqual(result["results"][0]["source"], "Example News")
        self.assertEqual(result["results"][0]["date"], "2025-07-23")
        mock_ddgs.news.assert_called_once()

    def test_search_exception_returns_error(self):
        mock_ddgs = _make_mock_ddgs()
        mock_ddgs.text.side_effect = RuntimeError("network error")

        with _patch_ddgs(mock_ddgs):
            result = run({"query": "anything"}, {})

        self.assertIn("error", result)
        self.assertIn("network error", result["error"])

    def test_missing_ddgs_returns_error(self):
        # Intercept the dynamic import inside run() to simulate ddgs not being installed.
        _real_import = __import__

        def _block_ddgs(name, *args, **kwargs):
            if name == "ddgs":
                raise ImportError("No module named 'ddgs'")
            return _real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_block_ddgs):
            result = run({"query": "hello"}, {})

        self.assertIn("error", result)
        self.assertIn("ddgs", result["error"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ddgs(*, text_results=None, news_results=None):
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    if text_results is not None:
        mock.text.return_value = text_results
    if news_results is not None:
        mock.news.return_value = news_results
    return mock


def _patch_ddgs(mock_ddgs_instance):
    """Return a context manager that patches the ddgs module used inside run()."""
    fake_module = types.ModuleType("ddgs")
    fake_module.DDGS = MagicMock(return_value=mock_ddgs_instance)
    return patch.dict("sys.modules", {"ddgs": fake_module})


if __name__ == "__main__":
    unittest.main()
