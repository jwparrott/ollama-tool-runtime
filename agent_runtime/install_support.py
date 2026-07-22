from __future__ import annotations

import argparse
import difflib
import html
import re
import sys
from typing import Iterable
from urllib import error, request


DEFAULT_SUGGESTED_MODELS = [
    "llama3.1",
    "deepseek-r1",
    "nomic-embed-text",
    "llama3.2",
    "gemma3",
]
OLLAMA_LIBRARY_URL = "https://ollama.com/library?sort=popular"
MODEL_LINK_PATTERN = re.compile(r'href="/library/([^"/?#]+)"')
SIZE_SUFFIX_PATTERN = re.compile(r"^(?P<family>.+?)\s+(?P<size>\d+(?:\.\d+)?[bm])$", re.IGNORECASE)


def _normalize_model_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.strip().lower())


def fetch_suggested_models(limit: int = 5, url: str = OLLAMA_LIBRARY_URL, timeout: int = 10) -> list[str]:
    try:
        req = request.Request(url, headers={"User-Agent": "ollama-tool-runtime-installer/1.0"})
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except (error.URLError, TimeoutError, OSError):
        return DEFAULT_SUGGESTED_MODELS[:limit]

    suggestions: list[str] = []
    seen: set[str] = set()
    for match in MODEL_LINK_PATTERN.finditer(payload):
        model_name = html.unescape(match.group(1)).strip()
        if not model_name or model_name == "library" or model_name in seen:
            continue
        seen.add(model_name)
        suggestions.append(model_name)
        if len(suggestions) >= limit:
            return suggestions
    return DEFAULT_SUGGESTED_MODELS[:limit]


def _unique_match(query: str, suggestions: Iterable[str], allow_fuzzy: bool = True) -> str | None:
    query_norm = _normalize_model_name(query)
    if not query_norm:
        return None

    exact_matches = [item for item in suggestions if item.lower() == query.strip().lower()]
    if exact_matches:
        return exact_matches[0]

    normalized_matches = [item for item in suggestions if _normalize_model_name(item) == query_norm]
    if normalized_matches:
        return normalized_matches[0]

    prefix_matches = [item for item in suggestions if _normalize_model_name(item).startswith(query_norm)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    contains_matches = [item for item in suggestions if query_norm in _normalize_model_name(item)]
    if len(contains_matches) == 1:
        return contains_matches[0]

    if allow_fuzzy:
        normalized_map = {_normalize_model_name(item): item for item in suggestions}
        close_matches = difflib.get_close_matches(query_norm, normalized_map.keys(), n=1, cutoff=0.72)
        if close_matches:
            return normalized_map[close_matches[0]]
    return None


def resolve_manual_model_name(name: str, suggestions: Iterable[str]) -> str:
    raw_name = name.strip()
    if not raw_name:
        raise ValueError("Model name cannot be blank.")

    matched = _unique_match(raw_name, suggestions, allow_fuzzy=False)
    if matched is not None:
        return matched

    compact = re.sub(r"[:/_-]+", " ", raw_name)
    compact = re.sub(r"\s+", " ", compact).strip()
    size_match = SIZE_SUFFIX_PATTERN.match(compact)
    if size_match is not None:
        family_match = _unique_match(size_match.group("family"), suggestions)
        if family_match is not None:
            return f"{family_match}:{size_match.group('size').lower()}"

    fuzzy_matched = _unique_match(raw_name, suggestions, allow_fuzzy=True)
    if fuzzy_matched is not None:
        return fuzzy_matched

    return raw_name


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Installer support helpers.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_models = sub.add_parser("list-models", help="List suggested models from Ollama.")
    list_models.add_argument("--limit", type=int, default=5, help="Maximum number of suggestions to return")

    resolve_model = sub.add_parser("resolve-model", help="Resolve a manual model name against suggested models.")
    resolve_model.add_argument("--name", default="", help="Model name to resolve. Reads stdin if omitted.")
    resolve_model.add_argument("--limit", type=int, default=5, help="Maximum number of suggestions to fetch")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-models":
        for model_name in fetch_suggested_models(limit=args.limit):
            print(model_name)
        return 0

    if args.command == "resolve-model":
        raw_name = args.name.strip() or sys.stdin.read().strip()
        resolved_name = resolve_manual_model_name(raw_name, fetch_suggested_models(limit=args.limit))
        print(resolved_name)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
