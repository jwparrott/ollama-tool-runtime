"""Read file contents with optional line range, restricted to the project root."""

from __future__ import annotations

import os
from pathlib import Path

TOOL_SPEC = {
    "name": "read_file",
    "description": (
        "Read the contents of a file. "
        "Paths are relative to the project root (absolute paths are also accepted but "
        "must be inside the project root). "
        "Use start_line and end_line (1-based, inclusive) to read a specific range. "
        "Returns the file content with line numbers prefixed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read (relative to project root or absolute).",
            },
            "start_line": {
                "type": "integer",
                "description": "First line to return (1-based, inclusive). Omit for start of file.",
            },
            "end_line": {
                "type": "integer",
                "description": "Last line to return (1-based, inclusive). Omit for end of file.",
            },
        },
        "required": ["path"],
    },
}

_MAX_CHARS = 20_000  # truncate large files to avoid flooding the context window


def run(args: dict, context: dict) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    raw_path = str(args["path"]).strip()

    target = (project_root / raw_path).resolve() if not os.path.isabs(raw_path) else Path(raw_path).resolve()

    try:
        target.relative_to(project_root)
    except ValueError:
        return {"error": f"Path is outside the project root: {target}"}

    if not target.exists():
        return {"error": f"File not found: {target}"}
    if target.is_dir():
        entries = sorted(str(p.relative_to(project_root)) for p in target.iterdir())
        return {"type": "directory", "path": str(target.relative_to(project_root)), "entries": entries}

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"error": f"Could not read file: {exc}"}

    lines = text.splitlines(keepends=True)
    total_lines = len(lines)

    start = max(1, int(args.get("start_line") or 1)) - 1  # 0-indexed
    end = min(total_lines, int(args.get("end_line") or total_lines))  # 1-indexed inclusive

    if start >= total_lines:
        return {"error": f"start_line {start + 1} exceeds file length ({total_lines} lines)"}

    selected = lines[start:end]
    numbered = "".join(f"{start + i + 1:4}. {line}" for i, line in enumerate(selected))

    truncated = False
    if len(numbered) > _MAX_CHARS:
        numbered = numbered[:_MAX_CHARS]
        truncated = True

    return {
        "path": str(target.relative_to(project_root)),
        "total_lines": total_lines,
        "returned_lines": f"{start + 1}-{start + len(selected)}",
        "truncated": truncated,
        "content": numbered,
    }
