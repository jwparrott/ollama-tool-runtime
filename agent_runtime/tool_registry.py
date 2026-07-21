from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ToolFunc = Callable[[dict[str, Any], dict[str, Any]], Any]


@dataclass
class ToolEntry:
    name: str
    module: str
    enabled: bool = True


class ToolRegistry:
    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save_entries([])

    def _load_entries(self) -> list[ToolEntry]:
        raw = json.loads(self.registry_path.read_text(encoding="utf-8") or "[]")
        return [ToolEntry(**item) for item in raw]

    def _save_entries(self, entries: list[ToolEntry]) -> None:
        payload = [entry.__dict__ for entry in entries]
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def list_entries(self) -> list[ToolEntry]:
        return self._load_entries()

    def add_entry(self, name: str, module: str) -> None:
        entries = self._load_entries()
        if any(entry.name == name for entry in entries):
            raise ValueError(f"Tool '{name}' already exists.")
        entries.append(ToolEntry(name=name, module=module, enabled=True))
        self._save_entries(entries)

    def _import_fresh(self, module_name: str) -> Any:
        importlib.invalidate_caches()
        if module_name in sys.modules:
            del sys.modules[module_name]
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            raise ModuleNotFoundError(f"Could not resolve module '{module_name}'.")
        source_path = Path(spec.origin)
        source = source_path.read_text(encoding="utf-8")
        module = types.ModuleType(module_name)
        module.__file__ = str(source_path)
        module.__package__ = module_name.rpartition(".")[0]
        code = compile(source, str(source_path), "exec")
        exec(code, module.__dict__)
        sys.modules[module_name] = module
        return module

    def get_callable(self, name: str) -> ToolFunc:
        entry = next((e for e in self._load_entries() if e.name == name and e.enabled), None)
        if entry is None:
            raise KeyError(f"Tool '{name}' not found.")
        module = self._import_fresh(entry.module)
        tool_func = getattr(module, "run", None)
        if tool_func is None or not callable(tool_func):
            raise RuntimeError(f"Tool module '{entry.module}' does not define callable run(args, context).")
        return tool_func

    def get_specs(self) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        for entry in self._load_entries():
            if not entry.enabled:
                continue
            try:
                module = self._import_fresh(entry.module)
            except (ModuleNotFoundError, FileNotFoundError, SyntaxError, ImportError):
                continue
            spec = getattr(module, "TOOL_SPEC", None)
            if not isinstance(spec, dict):
                continue
            specs.append(
                {
                    "type": "function",
                    "function": spec,
                }
            )
        return specs
