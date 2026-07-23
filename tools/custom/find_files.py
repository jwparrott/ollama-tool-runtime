"""Find files matching a glob pattern, restricted to the project root."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

TOOL_SPEC = {
    "name": "find_files",
    "description": (
        "Find files and directories by glob pattern. "
        "Patterns use standard glob syntax: * matches within a segment, "
        "** matches across multiple segments, ? matches any single character, "
        "and {a,b} is not supported (use separate calls). "
        "All results are relative to the project root. "
        "Examples: '**/*.py' finds all Python files, 'tests/test_*.py' finds test files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match files against (e.g. '**/*.py', 'src/*.ts').",
            },
            "base_path": {
                "type": "string",
                "description": (
                    "Directory to search within, relative to project root. "
                    "Defaults to the project root."
                ),
            },
            "include_dirs": {
                "type": "boolean",
                "description": "If true, include matching directories in results. Default false.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return. Default 200.",
            },
        },
        "required": ["pattern"],
    },
}

# Directories that are almost never useful to glob into.
_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", ".env", "dist", "build", ".runtime",
})


def run(args: dict, context: dict) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    pattern = str(args["pattern"]).strip()
    include_dirs = bool(args.get("include_dirs", False))
    max_results = min(max(1, int(args.get("max_results", 200))), 1000)

    raw_base = str(args.get("base_path") or "").strip()
    base = (project_root / raw_base).resolve() if raw_base else project_root

    try:
        base.relative_to(project_root)
    except ValueError:
        return {"error": f"base_path is outside the project root: {base}"}

    if not base.exists():
        return {"error": f"base_path does not exist: {base.relative_to(project_root)}"}

    matches: list[str] = []
    for path in _walk(base, _SKIP_DIRS):
        if not include_dirs and path.is_dir():
            continue
        rel = path.relative_to(project_root)
        if fnmatch.fnmatch(str(rel).replace("\\", "/"), pattern) or fnmatch.fnmatch(path.name, pattern):
            matches.append(str(rel))
        if len(matches) >= max_results:
            break

    return {
        "pattern": pattern,
        "base_path": str(base.relative_to(project_root)) if base != project_root else ".",
        "result_count": len(matches),
        "truncated": len(matches) == max_results,
        "matches": sorted(matches),
    }


def _walk(root: Path, skip: frozenset[str]):
    """Yield all paths under root, skipping directories in skip."""
    for entry in sorted(root.iterdir(), key=lambda p: (p.is_dir(), p.name)):
        if entry.name in skip:
            continue
        yield entry
        if entry.is_dir():
            yield from _walk(entry, skip)
