"""Firecrawl API integration for scrape/crawl/map operations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

TOOL_SPEC = {
    "name": "firecrawl_client",
    "description": (
        "Use Firecrawl API for advanced web scraping and crawling. "
        "Supports scrape, crawl, and map actions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["scrape", "crawl", "map"],
                "description": "Firecrawl action to perform.",
            },
            "api_key": {
                "type": "string",
                "description": "Firecrawl API key (optional if FIRECRAWL_API_KEY env is set).",
            },
            "url": {"type": "string", "description": "Target URL."},
            "formats": {
                "type": "array",
                "description": "Requested output formats for scrape (e.g. ['markdown']).",
                "items": {"type": "string"},
            },
            "limit": {"type": "integer", "description": "Page limit for crawl/map where supported."},
            "max_depth": {"type": "integer", "description": "Max crawl depth (crawl)."},
            "include_paths": {"type": "array", "items": {"type": "string"}, "description": "Path allow-list regexes."},
            "exclude_paths": {"type": "array", "items": {"type": "string"}, "description": "Path deny-list regexes."},
            "search": {"type": "string", "description": "Optional map search query."},
        },
        "required": ["action", "url"],
    },
}

_BASE_URL = "https://api.firecrawl.dev/v1"


def run(args: dict, context: dict) -> dict:
    _ = context
    action = str(args.get("action", "")).strip().lower()
    url = str(args.get("url", "")).strip()
    if action not in {"scrape", "crawl", "map"}:
        return {"error": "action must be one of: scrape, crawl, map"}
    if not url:
        return {"error": "url is required"}
    if urlparse(url).scheme.lower() not in {"http", "https"}:
        return {"error": f"url must start with http:// or https://. Got: {url!r}"}

    api_key = str(args.get("api_key") or os.environ.get("FIRECRAWL_API_KEY", "")).strip()
    if not api_key:
        return {"error": "Firecrawl API key is required (arg api_key or env FIRECRAWL_API_KEY)."}

    payload: dict = {"url": url}
    if action == "scrape":
        formats = args.get("formats")
        if isinstance(formats, list) and formats:
            payload["formats"] = [str(x) for x in formats]
    elif action == "crawl":
        if "limit" in args:
            payload["limit"] = int(args["limit"])
        if "max_depth" in args:
            payload["maxDepth"] = int(args["max_depth"])
        if isinstance(args.get("include_paths"), list):
            payload["includePaths"] = [str(x) for x in args["include_paths"]]
        if isinstance(args.get("exclude_paths"), list):
            payload["excludePaths"] = [str(x) for x in args["exclude_paths"]]
    else:  # map
        if "limit" in args:
            payload["limit"] = int(args["limit"])
        if str(args.get("search", "")).strip():
            payload["search"] = str(args["search"]).strip()

    endpoint = f"{_BASE_URL}/{action}"
    response = _post_json(endpoint, payload, api_key)
    if "error" in response:
        return response
    return {"ok": True, "action": action, "response": response}


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ollama-tool-runtime/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"error": f"Firecrawl HTTP {exc.code}: {detail}"}
    except urllib.error.URLError as exc:
        return {"error": f"Firecrawl request failed: {exc.reason}"}
    except TimeoutError:
        return {"error": "Firecrawl request timed out."}
    except OSError as exc:
        return {"error": f"Firecrawl request error: {exc}"}

    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"error": "Firecrawl returned invalid JSON."}
    return parsed if isinstance(parsed, dict) else {"data": parsed}
