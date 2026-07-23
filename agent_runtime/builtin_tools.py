from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from agent_runtime.skills import get_model_skill, list_model_skills
from agent_runtime.self_update import SelfUpdater
from agent_runtime.snapshots import SnapshotManager
from agent_runtime.tool_registry import ToolRegistry


def _safe_tool_name(name: str) -> str:
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name):
        raise ValueError("Tool name must match [a-zA-Z_][a-zA-Z0-9_]*")
    return name


class BuiltinTools:
    def __init__(
        self,
        project_root: Path,
        registry: ToolRegistry,
        snapshots: SnapshotManager,
        updater: SelfUpdater,
    ) -> None:
        self.project_root = project_root
        self.registry = registry
        self.snapshots = snapshots
        self.updater = updater

    def specs(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "register_python_tool",
                    "description": "Create a new python tool module and register it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "parameters_schema_json": {"type": "string"},
                            "source_code": {"type": "string"},
                        },
                        "required": ["name", "description", "parameters_schema_json", "source_code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_model_skills",
                    "description": "List built-in workflow skills/playbooks the model can follow.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_model_skill",
                    "description": "Get one workflow skill/playbook by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "self_update_files",
                    "description": "Update one or more files. If tests fail, rollback automatically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "files_json": {
                                "type": "string",
                                "description": "JSON object mapping relative file paths to full new file contents.",
                            },
                            "note": {"type": "string"},
                            "test_command": {"type": "string"},
                        },
                        "required": ["files_json", "note"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_tests",
                    "description": "Run test command and return output.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "test_command": {"type": "string"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_snapshots",
                    "description": "List available rollback snapshots.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "rollback_snapshot",
                    "description": "Restore a previous snapshot by id.",
                    "parameters": {
                        "type": "object",
                        "properties": {"snapshot_id": {"type": "string"}},
                        "required": ["snapshot_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tools",
                    "description": "List all currently available tools.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def dispatch(self) -> dict[str, Callable[[dict[str, Any]], Any]]:
        return {
            "register_python_tool": self.register_python_tool,
            "self_update_files": self.self_update_files,
            "run_tests": self.run_tests,
            "list_model_skills": self.list_model_skills,
            "get_model_skill": self.get_model_skill,
            "list_snapshots": self.list_snapshots,
            "rollback_snapshot": self.rollback_snapshot,
            "list_tools": self.list_tools,
        }

    def register_python_tool(self, args: dict[str, Any]) -> dict[str, Any]:
        required = ("name", "description", "source_code", "parameters_schema_json")
        missing = [f for f in required if not args.get(f)]
        if missing:
            raise ValueError(
                f"register_python_tool requires: {', '.join(required)}. "
                f"Missing or empty: {', '.join(missing)}"
            )
        name = _safe_tool_name(str(args["name"]))
        description = str(args["description"])
        source_code = str(args["source_code"])
        parameters_schema_json = str(args["parameters_schema_json"])
        parameters_schema = json.loads(parameters_schema_json)

        if any(entry.name == name for entry in self.registry.list_entries()):
            raise ValueError(f"Tool '{name}' already exists.")

        tool_path = self.project_root / "tools" / "custom" / f"{name}.py"
        if tool_path.exists():
            raise ValueError(f"Tool file already exists: {tool_path}")
        tool_path.parent.mkdir(parents=True, exist_ok=True)
        module_name = f"tools.custom.{name}"

        source_lines = source_code.rstrip().splitlines() or ["return {}"]
        indented_source = "\n".join(f"    {line}" if line.strip() else "" for line in source_lines)

        module_text = (
            "TOOL_SPEC = {\n"
            f"    \"name\": \"{name}\",\n"
            f"    \"description\": {json.dumps(description)},\n"
            f"    \"parameters\": {json.dumps(parameters_schema, indent=2)},\n"
            "}\n\n"
            "def run(args, context):\n"
            "    # User-provided implementation starts here.\n"
            f"{indented_source}\n"
        )
        tool_path.write_text(module_text, encoding="utf-8")

        self.registry.add_entry(name=name, module=module_name)
        return {"ok": True, "name": name, "module": module_name, "path": str(tool_path)}

    def self_update_files(self, args: dict[str, Any]) -> dict[str, Any]:
        files = json.loads(str(args["files_json"]))
        note = str(args["note"])
        test_command = str(args["test_command"]) if "test_command" in args and args["test_command"] else None
        if not isinstance(files, dict):
            raise ValueError("files_json must decode to an object of path -> content")
        return self.updater.update_files(files=files, note=note, test_command=test_command)

    def run_tests(self, args: dict[str, Any]) -> dict[str, Any]:
        test_command = str(args["test_command"]) if "test_command" in args and args["test_command"] else None
        return self.updater.run_tests(command=test_command)

    def list_model_skills(self, args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return {"skills": list_model_skills()}

    def get_model_skill(self, args: dict[str, Any]) -> dict[str, Any]:
        if "name" not in args or not str(args["name"]).strip():
            raise ValueError("get_model_skill requires non-empty 'name'.")
        return {"skill": get_model_skill(str(args["name"]))}

    def list_snapshots(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        _ = args
        return [record.__dict__ for record in self.snapshots.list()]

    def rollback_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = str(args["snapshot_id"])
        self.snapshots.restore(snapshot_id)
        return {"ok": True, "restored_snapshot_id": snapshot_id}

    def list_tools(self, args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return {
            "builtin": [spec["function"]["name"] for spec in self.specs()],
            "custom": [entry.__dict__ for entry in self.registry.list_entries()],
        }
