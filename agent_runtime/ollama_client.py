from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class OllamaClient:
    def __init__(self, base_url: str) -> None:
        self._chat_url = f"{base_url.rstrip('/')}/api/chat"

    def chat(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(self._chat_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama request failed: HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Cannot connect to Ollama at {self._chat_url}: {exc}") from exc

