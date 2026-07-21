from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from agent_runtime.tool_registry import ToolRegistry


class ToolRegistryTests(unittest.TestCase):
    def test_add_and_list_entries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry_path = Path(td) / "tools" / "registry.json"
            registry = ToolRegistry(registry_path)
            registry.add_entry("sample", "tools.custom.sample")
            entries = registry.list_entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].name, "sample")
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["module"], "tools.custom.sample")

    def test_reload_picks_up_tool_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "mypkg"
            pkg.mkdir(parents=True, exist_ok=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            tool_file = pkg / "tool.py"
            tool_file.write_text(
                "TOOL_SPEC = {'name': 'x', 'description': 'x', 'parameters': {'type':'object','properties':{}}}\n"
                "def run(args, context):\n"
                "    return {'value': 1}\n",
                encoding="utf-8",
            )
            registry_path = root / "tools" / "registry.json"
            registry = ToolRegistry(registry_path)
            registry.add_entry("x", "mypkg.tool")

            sys.path.insert(0, str(root))
            try:
                first = registry.get_callable("x")({}, {})
                self.assertEqual(first["value"], 1)

                tool_file.write_text(
                    "TOOL_SPEC = {'name': 'x', 'description': 'x', 'parameters': {'type':'object','properties':{}}}\n"
                    "def run(args, context):\n"
                    "    return {'value': 2}\n",
                    encoding="utf-8",
                )
                second = registry.get_callable("x")({}, {})
                self.assertEqual(second["value"], 2)
            finally:
                sys.modules.pop("mypkg.tool", None)
                sys.modules.pop("mypkg", None)
                sys.path.remove(str(root))

    def test_get_callable_reloads_updated_module(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module_dir = root / "tmpmods" / "custom"
            module_dir.mkdir(parents=True, exist_ok=True)
            (root / "tmpmods" / "__init__.py").write_text("", encoding="utf-8")
            (module_dir / "__init__.py").write_text("", encoding="utf-8")

            module_path = module_dir / "sample.py"
            module_path.write_text(
                "TOOL_SPEC = {'name': 'sample', 'description': 'v1', 'parameters': {'type': 'object'}}\n"
                "def run(args, context):\n"
                "    return {'value': 1}\n",
                encoding="utf-8",
            )

            registry = ToolRegistry(root / "registry.json")
            registry.add_entry("sample", "tmpmods.custom.sample")

            sys.path.insert(0, str(root))
            try:
                first = registry.get_callable("sample")
                self.assertEqual(first({}, {})["value"], 1)

                module_path.write_text(
                    "TOOL_SPEC = {'name': 'sample', 'description': 'v2', 'parameters': {'type': 'object'}}\n"
                    "def run(args, context):\n"
                    "    return {'value': 2}\n",
                    encoding="utf-8",
                )

                second = registry.get_callable("sample")
                self.assertEqual(second({}, {})["value"], 2)
            finally:
                sys.path.remove(str(root))
                for mod in [name for name in list(sys.modules) if name == "tmpmods" or name.startswith("tmpmods.")]:
                    del sys.modules[mod]

    def test_get_specs_skips_broken_module(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module_dir = root / "tmpmods" / "custom"
            module_dir.mkdir(parents=True, exist_ok=True)
            (root / "tmpmods" / "__init__.py").write_text("", encoding="utf-8")
            (module_dir / "__init__.py").write_text("", encoding="utf-8")

            (module_dir / "good.py").write_text(
                "TOOL_SPEC = {'name': 'good', 'description': 'ok', 'parameters': {'type': 'object'}}\n"
                "def run(args, context):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            (module_dir / "bad.py").write_text("def broken(:\n", encoding="utf-8")

            registry = ToolRegistry(root / "registry.json")
            registry.add_entry("good", "tmpmods.custom.good")
            registry.add_entry("bad", "tmpmods.custom.bad")

            sys.path.insert(0, str(root))
            try:
                specs = registry.get_specs()
            finally:
                sys.path.remove(str(root))
                for mod in [name for name in list(sys.modules) if name == "tmpmods" or name.startswith("tmpmods.")]:
                    del sys.modules[mod]

            self.assertEqual(len(specs), 1)
            self.assertEqual(specs[0]["function"]["name"], "good")


if __name__ == "__main__":
    unittest.main()
