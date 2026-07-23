"""Unified web data pipeline to reduce overlap between search/fetch/scrape tools."""

from __future__ import annotations

from typing import Any

TOOL_SPEC = {
    "name": "web_data_pipeline",
    "description": (
        "Unified web workflow: search, fetch, and scrape in one tool. "
        "Use this to reduce redundancy between separate web_search/fetch_url/firecrawl tools."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "fetch", "scrape"],
                "description": "Pipeline action to perform.",
            },
            "query": {"type": "string", "description": "Search query (for action=search)."},
            "url": {"type": "string", "description": "URL (for action=fetch/scrape)."},
            "max_results": {"type": "integer", "description": "Search results limit (default 5)."},
            "search_type": {"type": "string", "enum": ["text", "news"], "description": "Search mode for search action."},
            "raw": {"type": "boolean", "description": "Return raw HTML/body for fetch action."},
            "max_chars": {"type": "integer", "description": "Character limit for fetch output."},
            "start_index": {"type": "integer", "description": "Pagination offset for fetch output."},
            "api_key": {"type": "string", "description": "Firecrawl API key for scrape action."},
            "formats": {"type": "array", "items": {"type": "string"}, "description": "Firecrawl scrape formats."},
        },
        "required": ["action"],
    },
}


def run(args: dict, context: dict) -> dict:
    action = str(args.get("action", "")).strip().lower()
    if action == "search":
        from tools.custom.web_search import run as web_search_run

        payload = {
            "query": args.get("query", ""),
            "max_results": args.get("max_results", 5),
            "search_type": args.get("search_type", "text"),
        }
        result = web_search_run(payload, context)
        return {"action": "search", **result}
    if action == "fetch":
        from tools.custom.fetch_url import run as fetch_url_run

        payload = {
            "url": args.get("url", ""),
            "raw": args.get("raw", False),
            "max_chars": args.get("max_chars", 5000),
            "start_index": args.get("start_index", 0),
        }
        result = fetch_url_run(payload, context)
        return {"action": "fetch", **result}
    if action == "scrape":
        from tools.custom.firecrawl_client import run as firecrawl_run

        payload: dict[str, Any] = {
            "action": "scrape",
            "url": args.get("url", ""),
            "formats": args.get("formats", ["markdown"]),
        }
        if args.get("api_key"):
            payload["api_key"] = args["api_key"]
        result = firecrawl_run(payload, context)
        return {"action": "scrape", **result}
    return {"error": "action must be one of: search, fetch, scrape"}
