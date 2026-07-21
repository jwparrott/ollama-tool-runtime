from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    project_root: Path
    ollama_url: str = "http://127.0.0.1:11434"
    registry_file: str = "tools/registry.json"
    snapshot_dir: str = ".runtime/snapshots"
    settings_file: str = ".runtime/settings.json"
    default_test_command: str = "python -m unittest discover -s tests"

    @property
    def registry_path(self) -> Path:
        return self.project_root / self.registry_file

    @property
    def snapshots_path(self) -> Path:
        return self.project_root / self.snapshot_dir

    @property
    def settings_path(self) -> Path:
        return self.project_root / self.settings_file
