"""Targeted string replacement in a file, restricted to the project root."""

from __future__ import annotations

import os
from pathlib import Path

TOOL_SPEC = {
    "name": "edit_file",
    "description": (
        "Make a precise, surgical edit to an existing file by replacing an exact string. "
        "old_str must match exactly one location in the file (it is rejected if it appears "
        "zero or more than once). Include enough surrounding context in old_str to make it "
        "unique. Paths are relative to the project root."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to edit (relative to project root or absolute).",
            },
            "old_str": {
                "type": "string",
                "description": "The exact string to find and replace. Must appear exactly once.",
            },
            "new_str": {
                "type": "string",
                "description": "The replacement string. Use empty string to delete old_str.",
            },
        },
        "required": ["path", "old_str", "new_str"],
    },
}


def run(args: dict, context: dict) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    raw_path = str(args["path"]).strip()
    old_str = str(args["old_str"])
    new_str = str(args["new_str"])

    target = (project_root / raw_path).resolve() if not os.path.isabs(raw_path) else Path(raw_path).resolve()

    try:
        target.relative_to(project_root)
    except ValueError:
        return {"error": f"Path is outside the project root: {target}"}

    if not target.exists():
        return {"error": f"File not found: {target}"}
    if target.is_dir():
        return {"error": f"Path is a directory, not a file: {target}"}

    try:
        original = target.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": f"Could not read file: {exc}"}

    count = original.count(old_str)
    if count == 0:
        return {
            "error": (
                "old_str was not found in the file. "
                "Check for whitespace, indentation, or line ending differences."
            )
        }
    if count > 1:
        return {
            "error": (
                f"old_str appears {count} times in the file. "
                "Include more surrounding context to make it unique."
            )
        }

    updated = original.replace(old_str, new_str, 1)
    try:
        target.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return {"error": f"Could not write file: {exc}"}

    return {
        "ok": True,
        "path": str(target.relative_to(project_root)),
        "chars_before": len(original),
        "chars_after": len(updated),
    }
