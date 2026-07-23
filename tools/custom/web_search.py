"""Web search tool using DuckDuckGo — no API key required."""

from __future__ import annotations

TOOL_SPEC = {
    "name": "web_search",
    "description": (
        "Search the web using DuckDuckGo and return real-time results. "
        "Use this for current events, facts, documentation, or anything "
        "that may have changed after your training cutoff. "
        "Returns a list of results each with a title, URL, and snippet."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-10, default 5).",
            },
            "search_type": {
                "type": "string",
                "enum": ["text", "news"],
                "description": "Type of search: 'text' for general web results (default), 'news' for recent news articles.",
            },
        },
        "required": ["query"],
    },
}


def run(args: dict, context: dict) -> dict:
    _ = context
    query: str = str(args["query"]).strip()
    if not query:
        return {"error": "query must not be empty"}

    max_results: int = min(max(1, int(args.get("max_results", 5))), 10)
    search_type: str = str(args.get("search_type", "text")).lower()
    if search_type not in ("text", "news"):
        search_type = "text"

    try:
        from ddgs import DDGS  # type: ignore[import]
    except ImportError:
        return {
            "error": (
                "The 'ddgs' package is not installed. "
                "Run: pip install ddgs"
            )
        }

    try:
        with DDGS() as ddgs:
            if search_type == "news":
                raw = ddgs.news(query, max_results=max_results)
                results = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("body", ""),
                        "source": r.get("source", ""),
                        "date": r.get("date", ""),
                    }
                    for r in raw
                ]
            else:
                raw = ddgs.text(query, max_results=max_results)
                results = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                    for r in raw
                ]
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Search failed: {exc}"}

    return {
        "query": query,
        "search_type": search_type,
        "result_count": len(results),
        "results": results,
    }
