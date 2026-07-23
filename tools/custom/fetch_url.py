"""Fetch a URL and return its content as simplified text or raw HTML."""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

TOOL_SPEC = {
    "name": "fetch_url",
    "description": (
        "Fetch a web page or URL and return its content. "
        "By default converts HTML to readable plain text (stripping tags, scripts, and styles). "
        "Set raw=true to get the raw HTML/response body instead. "
        "Use max_chars and start_index for pagination of large pages. "
        "Useful for reading documentation, checking APIs, or fetching specific web content."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch (must start with http:// or https://).",
            },
            "raw": {
                "type": "boolean",
                "description": "If true, return raw HTML/body instead of plain text. Default false.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (1-20000). Default 5000.",
            },
            "start_index": {
                "type": "integer",
                "description": "Character offset for pagination (default 0). Use to read subsequent pages.",
            },
        },
        "required": ["url"],
    },
}

_DEFAULT_MAX = 5_000
_HARD_MAX = 20_000
_TIMEOUT = 15  # seconds

_USER_AGENT = (
    "Mozilla/5.0 (compatible; OllamaToolRuntime/1.0; +https://github.com/jwparrott/ollama-tool-runtime)"
)


def run(args: dict, context: dict) -> dict:
    _ = context
    url = str(args["url"]).strip()
    raw = bool(args.get("raw", False))
    max_chars = min(max(1, int(args.get("max_chars", _DEFAULT_MAX))), _HARD_MAX)
    start_index = max(0, int(args.get("start_index", 0)))

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"error": f"URL must start with http:// or https://. Got: {url!r}"}

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body_bytes = resp.read(512 * 1024)  # cap at 512 KB to avoid huge downloads
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}: {exc.reason}", "url": url}
    except urllib.error.URLError as exc:
        return {"error": f"Request failed: {exc.reason}", "url": url}
    except TimeoutError:
        return {"error": f"Request timed out after {_TIMEOUT}s", "url": url}
    except OSError as exc:
        return {"error": f"Request error: {exc}", "url": url}

    encoding = _detect_encoding(content_type) or "utf-8"
    try:
        body = body_bytes.decode(encoding, errors="replace")
    except LookupError:
        body = body_bytes.decode("utf-8", errors="replace")

    is_html = "html" in content_type.lower()
    if not raw and is_html:
        text = _html_to_text(body)
    else:
        text = body

    total_chars = len(text)
    chunk = text[start_index: start_index + max_chars]
    has_more = (start_index + max_chars) < total_chars

    return {
        "url": url,
        "content_type": content_type,
        "total_chars": total_chars,
        "start_index": start_index,
        "returned_chars": len(chunk),
        "has_more": has_more,
        "next_start_index": start_index + max_chars if has_more else None,
        "content": chunk,
    }


def _detect_encoding(content_type: str) -> str | None:
    m = re.search(r"charset=([^\s;]+)", content_type, re.IGNORECASE)
    return m.group(1).strip('"') if m else None


def _html_to_text(html_body: str) -> str:
    """Very lightweight HTML → plain text conversion (no dependencies)."""
    # Remove script and style blocks entirely
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_body, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    text = re.sub(r"<(br|p|div|h[1-6]|li|tr|blockquote)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
