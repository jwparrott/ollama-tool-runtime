from __future__ import annotations

import json
from typing import Any
from urllib import error, request


DEFAULT_TIMEOUT_SECONDS = 600


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._chat_url = f"{base_url.rstrip('/')}/api/chat"
        self._timeout = timeout_seconds

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        context_window_tokens: int,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "options": {"num_ctx": context_window_tokens},
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(self._chat_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except TimeoutError as exc:
            raise RuntimeError(
                f"Ollama request timed out after {self._timeout}s for model '{model}'. "
                "The model may still be loading into memory. "
                "Use --timeout to increase the limit, or try again in a moment."
            ) from exc
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama request failed: HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Cannot connect to Ollama at {self._chat_url}: {exc}") from exc
