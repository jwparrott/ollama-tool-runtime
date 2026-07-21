from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_runtime.builtin_tools import BuiltinTools
from agent_runtime.self_update import SelfUpdater
from agent_runtime.snapshots import SnapshotManager
from agent_runtime.tool_registry import ToolRegistry


class BuiltinToolsTests(unittest.TestCase):
    def test_register_python_tool_does_not_overwrite_existing_tool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            root.mkdir(parents=True, exist_ok=True)

            registry = ToolRegistry(root / "tools" / "registry.json")
            registry.add_entry("sample", "tools.custom.sample")

            tool_path = root / "tools" / "custom" / "sample.py"
            tool_path.parent.mkdir(parents=True, exist_ok=True)
            original_content = "TOOL_SPEC = {}\n\ndef run(args, context):\n    return {'ok': True}\n"
            tool_path.write_text(original_content, encoding="utf-8")

            snapshots = SnapshotManager(project_root=root, snapshots_dir=root / ".runtime" / "snapshots")
            updater = SelfUpdater(
                project_root=root,
                snapshots=snapshots,
                default_test_command='python -c "import sys; sys.exit(0)"',
            )
            builtins = BuiltinTools(project_root=root, registry=registry, snapshots=snapshots, updater=updater)

            with self.assertRaises(ValueError):
                builtins.register_python_tool(
                    {
                        "name": "sample",
                        "description": "duplicate",
                        "parameters_schema_json": '{"type":"object","properties":{}}',
                        "source_code": "return {'ok': False}",
                    }
                )

            self.assertEqual(tool_path.read_text(encoding="utf-8"), original_content)


if __name__ == "__main__":
    unittest.main()

