"""Fetch top Hacker News stories from the public HN Firebase API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib import request

TOOL_SPEC = {
    "name": "hackernews_top",
    "description": "Fetch top Hacker News stories in near real time.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of stories to return (1-30, default 10)."},
        },
    },
}


def run(args: dict, context: dict) -> dict:
    _ = context
    limit = min(max(1, int(args.get("limit", 10))), 30)

    ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if isinstance(ids, dict) and "error" in ids:
        return ids
    if not isinstance(ids, list):
        return {"error": "Unexpected topstories response format."}

    stories = []
    for item_id in ids[:limit]:
        story = _fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
        if not isinstance(story, dict):
            continue
        if story.get("type") != "story":
            continue
        timestamp = story.get("time")
        iso_time = None
        if isinstance(timestamp, int):
            iso_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        stories.append(
            {
                "id": story.get("id"),
                "title": story.get("title"),
                "url": story.get("url"),
                "author": story.get("by"),
                "score": story.get("score"),
                "comments": story.get("descendants"),
                "created_utc": iso_time,
            }
        )

    return {"result_count": len(stories), "stories": stories}


def _fetch_json(url: str):
    req = request.Request(url, headers={"User-Agent": "ollama-tool-runtime/1.0"})
    try:
        with request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except TimeoutError:
        return {"error": "Request timed out."}
    except OSError as exc:
        return {"error": f"Request failed: {exc}"}
    except json.JSONDecodeError:
        return {"error": "Remote service returned invalid JSON."}
