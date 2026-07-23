from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib import error

from agent_runtime.ollama_client import OllamaClient, DEFAULT_TIMEOUT_SECONDS


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class OllamaClientTests(unittest.TestCase):
    def test_default_timeout_is_600(self) -> None:
        self.assertEqual(DEFAULT_TIMEOUT_SECONDS, 600)
        client = OllamaClient("http://127.0.0.1:11434")
        self.assertEqual(client._timeout, 600)

    def test_custom_timeout_is_stored(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434", timeout_seconds=30)
        self.assertEqual(client._timeout, 30)

    def test_timeout_error_raises_runtime_error_with_hint(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434", timeout_seconds=5)
        with patch("agent_runtime.ollama_client.request.urlopen", side_effect=TimeoutError()):
            with self.assertRaises(RuntimeError) as ctx:
                client.chat(model="gemma4:12b", messages=[], tools=[], context_window_tokens=8192)
        self.assertIn("timed out", str(ctx.exception))
        self.assertIn("gemma4:12b", str(ctx.exception))
        self.assertIn("--timeout", str(ctx.exception))

    def test_http_error_raises_runtime_error(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434")
        http_err = error.HTTPError(url=None, code=404, msg="Not Found", hdrs=None, fp=None)  # type: ignore[arg-type]
        http_err.read = lambda: b"model not found"
        with patch("agent_runtime.ollama_client.request.urlopen", side_effect=http_err):
            with self.assertRaises(RuntimeError) as ctx:
                client.chat(model="bad", messages=[], tools=[], context_window_tokens=8192)
        self.assertIn("404", str(ctx.exception))

    def test_url_error_raises_runtime_error(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434")
        with patch("agent_runtime.ollama_client.request.urlopen", side_effect=error.URLError("refused")):
            with self.assertRaises(RuntimeError) as ctx:
                client.chat(model="any", messages=[], tools=[], context_window_tokens=8192)
        self.assertIn("Cannot connect", str(ctx.exception))

    def test_successful_chat_returns_parsed_json(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434")
        fake_response = _FakeResponse('{"message": {"content": "hello", "tool_calls": []}}')
        with patch("agent_runtime.ollama_client.request.urlopen", return_value=fake_response):
            result = client.chat(model="any", messages=[], tools=[], context_window_tokens=8192)
        self.assertEqual(result["message"]["content"], "hello")


if __name__ == "__main__":
    unittest.main()
