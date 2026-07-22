from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib import error

from agent_runtime.install_support import fetch_suggested_models, resolve_manual_model_name


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class InstallSupportTests(unittest.TestCase):
    def test_fetch_suggested_models_parses_popular_library_links(self) -> None:
        html = """
        <a href="/library/llama3.1">Llama</a>
        <a href="/library/deepseek-r1">DeepSeek</a>
        <a href="/library/llama3.1">Duplicate</a>
        <a href="/library/gemma3">Gemma</a>
        """
        with patch("agent_runtime.install_support.request.urlopen", return_value=_FakeResponse(html)):
            models = fetch_suggested_models(limit=3, url="https://example.test")
        self.assertEqual(models, ["llama3.1", "deepseek-r1", "gemma3"])

    def test_fetch_suggested_models_falls_back_when_request_fails(self) -> None:
        with patch("agent_runtime.install_support.request.urlopen", side_effect=error.URLError("boom")):
            models = fetch_suggested_models(limit=2, url="https://example.test")
        self.assertEqual(models, ["llama3.1", "deepseek-r1"])

    def test_resolve_manual_model_name_matches_normalized_name(self) -> None:
        resolved = resolve_manual_model_name("gemma 3", ["llama3.1", "gemma3"])
        self.assertEqual(resolved, "gemma3")

    def test_resolve_manual_model_name_builds_tagged_name(self) -> None:
        resolved = resolve_manual_model_name("deepseek r1 7B", ["deepseek-r1", "gemma3"])
        self.assertEqual(resolved, "deepseek-r1:7b")

    def test_resolve_manual_model_name_preserves_unknown_names(self) -> None:
        resolved = resolve_manual_model_name("my-special-model:latest", ["deepseek-r1", "gemma3"])
        self.assertEqual(resolved, "my-special-model:latest")


if __name__ == "__main__":
    unittest.main()
