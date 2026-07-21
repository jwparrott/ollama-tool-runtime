from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_runtime.self_update import SelfUpdater
from agent_runtime.snapshots import SnapshotManager


class SelfUpdateTests(unittest.TestCase):
    def test_failed_update_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            root.mkdir(parents=True, exist_ok=True)
            snapshots = SnapshotManager(project_root=root, snapshots_dir=root / ".runtime" / "snapshots")
            updater = SelfUpdater(
                project_root=root,
                snapshots=snapshots,
                default_test_command='python -c "import sys; sys.exit(0)"',
            )

            target = root / "target.txt"
            target.write_text("good", encoding="utf-8")
            result = updater.update_files(
                files={"target.txt": "bad"},
                note="test rollback",
                test_command='python -c "import sys; sys.exit(1)"',
            )
            self.assertFalse(result["ok"])
            self.assertEqual(target.read_text(encoding="utf-8"), "good")

    def test_invalid_path_rejected_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            root.mkdir(parents=True, exist_ok=True)
            snapshots = SnapshotManager(project_root=root, snapshots_dir=root / ".runtime" / "snapshots")
            updater = SelfUpdater(
                project_root=root,
                snapshots=snapshots,
                default_test_command='python -c "import sys; sys.exit(0)"',
            )

            target = root / "target.txt"
            target.write_text("good", encoding="utf-8")

            with self.assertRaises(ValueError):
                updater.update_files(
                    files={
                        "target.txt": "changed",
                        "..\\outside.txt": "bad",
                    },
                    note="invalid path should fail",
                )

            self.assertEqual(target.read_text(encoding="utf-8"), "good")
            self.assertEqual(snapshots.list(), [])


if __name__ == "__main__":
    unittest.main()
