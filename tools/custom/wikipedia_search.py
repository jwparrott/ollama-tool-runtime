"""Search Wikipedia with MediaWiki API and return concise structured results."""

from __future__ import annotations

import json
import re
from urllib import parse, request

TOOL_SPEC = {
    "name": "wikipedia_search",
    "description": (
        "Search Wikipedia and return matching pages with title, snippet, and URL. "
        "Useful for general knowledge lookups with citations."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query text."},
            "limit": {"type": "integer", "description": "Maximum results to return (1-20, default 5)."},
            "language": {
                "type": "string",
                "description": "Wikipedia language code such as 'en', 'de', or 'fr'. Default: en.",
            },
        },
        "required": ["query"],
    },
}


def run(args: dict, context: dict) -> dict:
    _ = context
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query must not be empty"}

    limit = min(max(1, int(args.get("limit", 5))), 20)
    language = str(args.get("language", "en")).strip().lower() or "en"
    if not re.fullmatch(r"[a-z]{2,12}", language):
        return {"error": "language must be a simple alphabetic code (e.g. 'en')."}

    params = parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": str(limit),
            "utf8": "1",
            "format": "json",
        }
    )
    url = f"https://{language}.wikipedia.org/w/api.php?{params}"
    req = request.Request(url, headers={"User-Agent": "ollama-tool-runtime/1.0"})

    try:
        with request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except TimeoutError:
        return {"error": "Wikipedia request timed out."}
    except OSError as exc:
        return {"error": f"Wikipedia request failed: {exc}"}
    except json.JSONDecodeError:
        return {"error": "Wikipedia returned invalid JSON."}

    raw_results = payload.get("query", {}).get("search", [])
    results = []
    for item in raw_results:
        title = str(item.get("title", ""))
        page_id = item.get("pageid")
        snippet = _strip_html(str(item.get("snippet", "")))
        page_url = f"https://{language}.wikipedia.org/wiki/{parse.quote(title.replace(' ', '_'))}"
        results.append(
            {
                "title": title,
                "pageid": page_id,
                "snippet": snippet,
                "url": page_url,
            }
        )

    return {"query": query, "language": language, "result_count": len(results), "results": results}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()
