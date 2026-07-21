from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from agent_runtime.snapshots import SnapshotManager


class SelfUpdater:
    def __init__(self, project_root: Path, snapshots: SnapshotManager, default_test_command: str) -> None:
        self.project_root = project_root
        self.snapshots = snapshots
        self.default_test_command = default_test_command

    def run_tests(self, command: str | None = None) -> dict[str, Any]:
        test_cmd = command or self.default_test_command
        process = subprocess.run(
            test_cmd,
            cwd=self.project_root,
            shell=True,
            text=True,
            capture_output=True,
        )
        return {
            "ok": process.returncode == 0,
            "command": test_cmd,
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }

    def _resolve_destination(self, relative_path: str) -> Path:
        destination = (self.project_root / relative_path).resolve()
        project_root = self.project_root.resolve()
        if project_root not in destination.parents and destination != project_root:
            raise ValueError(f"Refusing to write outside project root: {relative_path}")
        return destination

    def update_files(self, files: dict[str, str], note: str, test_command: str | None = None) -> dict[str, Any]:
        write_plan: list[tuple[Path, str]] = []
        for relative_path, content in files.items():
            if not isinstance(content, str):
                raise ValueError(f"Content for '{relative_path}' must be a string.")
            destination = self._resolve_destination(relative_path)
            write_plan.append((destination, content))

        snapshot = self.snapshots.create(note=note)
        try:
            for destination, content in write_plan:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.snapshots.restore(snapshot.id)
            return {
                "ok": False,
                "rolled_back_to": snapshot.id,
                "error": str(exc),
            }

        test_result = self.run_tests(test_command)
        if not test_result["ok"]:
            self.snapshots.restore(snapshot.id)
            return {
                "ok": False,
                "rolled_back_to": snapshot.id,
                "test_result": test_result,
            }

        return {
            "ok": True,
            "snapshot_id": snapshot.id,
            "test_result": test_result,
        }
