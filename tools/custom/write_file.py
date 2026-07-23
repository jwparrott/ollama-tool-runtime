"""Create or overwrite a file with given content, restricted to the project root."""

from __future__ import annotations

import os
from pathlib import Path

TOOL_SPEC = {
    "name": "write_file",
    "description": (
        "Create a new file or completely overwrite an existing file with the given content. "
        "Paths are relative to the project root. Parent directories are created automatically. "
        "Use edit_file for targeted in-place edits rather than full rewrites."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write (relative to project root or absolute).",
            },
            "content": {
                "type": "string",
                "description": "Full content to write to the file.",
            },
            "overwrite": {
                "type": "boolean",
                "description": (
                    "If false (default) and the file already exists, return an error instead "
                    "of overwriting. Set to true to allow overwriting existing files."
                ),
            },
        },
        "required": ["path", "content"],
    },
}


def run(args: dict, context: dict) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    raw_path = str(args["path"]).strip()
    content = str(args["content"])
    overwrite = bool(args.get("overwrite", False))

    target = (project_root / raw_path).resolve() if not os.path.isabs(raw_path) else Path(raw_path).resolve()

    try:
        target.relative_to(project_root)
    except ValueError:
        return {"error": f"Path is outside the project root: {target}"}

    if target.is_dir():
        return {"error": f"Path is a directory, not a file: {target}"}

    if target.exists() and not overwrite:
        return {
            "error": (
                f"File already exists: {target.relative_to(project_root)}. "
                "Set overwrite=true to replace it."
            )
        }

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"error": f"Could not write file: {exc}"}

    return {
        "ok": True,
        "path": str(target.relative_to(project_root)),
        "bytes_written": len(content.encode("utf-8")),
        "created": not target.exists() or overwrite,
    }
