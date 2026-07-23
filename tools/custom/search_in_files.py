"""Search file contents by regex pattern, restricted to the project root."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

TOOL_SPEC = {
    "name": "search_in_files",
    "description": (
        "Search file contents using a regular expression and return matching lines. "
        "Equivalent to grep. Returns each match with its file path, line number, and content. "
        "Use glob_pattern to restrict which files are searched (e.g. '**/*.py'). "
        "Use context_lines to include surrounding lines for better understanding."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regular expression to search for in file contents.",
            },
            "glob_pattern": {
                "type": "string",
                "description": (
                    "Glob pattern to filter which files are searched "
                    "(e.g. '**/*.py', '*.md'). Defaults to all files."
                ),
            },
            "base_path": {
                "type": "string",
                "description": "Directory to search within, relative to project root. Defaults to project root.",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "If true, perform case-insensitive matching. Default false.",
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of lines of context to include before and after each match (0-5). Default 0.",
            },
            "max_matches": {
                "type": "integer",
                "description": "Maximum total matches to return. Default 50.",
            },
        },
        "required": ["pattern"],
    },
}

_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", ".env", "dist", "build", ".runtime",
})

_BINARY_EXTENSIONS = frozenset({
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".obj",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
})


def run(args: dict, context: dict) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    pattern_str = str(args["pattern"])
    glob_pat = str(args.get("glob_pattern") or "").strip() or None
    case_insensitive = bool(args.get("case_insensitive", False))
    context_lines = min(max(0, int(args.get("context_lines", 0))), 5)
    max_matches = min(max(1, int(args.get("max_matches", 50))), 200)

    raw_base = str(args.get("base_path") or "").strip()
    base = (project_root / raw_base).resolve() if raw_base else project_root

    try:
        base.relative_to(project_root)
    except ValueError:
        return {"error": f"base_path is outside the project root: {base}"}

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern_str, flags)
    except re.error as exc:
        return {"error": f"Invalid regular expression: {exc}"}

    matches: list[dict] = []
    files_searched = 0

    for file_path in _iter_files(base, _SKIP_DIRS):
        if file_path.suffix.lower() in _BINARY_EXTENSIONS:
            continue
        if glob_pat:
            rel = str(file_path.relative_to(project_root)).replace("\\", "/")
            if not fnmatch.fnmatch(rel, glob_pat) and not fnmatch.fnmatch(file_path.name, glob_pat):
                continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        files_searched += 1
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if regex.search(line):
                entry: dict = {
                    "file": str(file_path.relative_to(project_root)),
                    "line": i + 1,
                    "content": line,
                }
                if context_lines > 0:
                    before = lines[max(0, i - context_lines): i]
                    after = lines[i + 1: i + 1 + context_lines]
                    entry["context_before"] = before
                    entry["context_after"] = after
                matches.append(entry)
                if len(matches) >= max_matches:
                    return _result(pattern_str, matches, files_searched, truncated=True)

    return _result(pattern_str, matches, files_searched, truncated=False)


def _result(pattern: str, matches: list, files_searched: int, *, truncated: bool) -> dict:
    return {
        "pattern": pattern,
        "files_searched": files_searched,
        "match_count": len(matches),
        "truncated": truncated,
        "matches": matches,
    }


def _iter_files(root: Path, skip: frozenset[str]):
    for entry in sorted(root.iterdir(), key=lambda p: (p.is_dir(), p.name)):
        if entry.name in skip:
            continue
        if entry.is_file():
            yield entry
        elif entry.is_dir():
            yield from _iter_files(entry, skip)
