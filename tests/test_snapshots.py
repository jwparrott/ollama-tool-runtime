from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_runtime.snapshots import SnapshotManager


class SnapshotTests(unittest.TestCase):
    def test_create_and_restore_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            root.mkdir(parents=True, exist_ok=True)
            snapshots_dir = root / ".runtime" / "snapshots"
            manager = SnapshotManager(project_root=root, snapshots_dir=snapshots_dir)

            file_path = root / "a.txt"
            file_path.write_text("v1", encoding="utf-8")
            snap = manager.create("before change")
            file_path.write_text("v2", encoding="utf-8")

            manager.restore(snap.id)
            self.assertEqual(file_path.read_text(encoding="utf-8"), "v1")
            self.assertTrue(snapshots_dir.exists())
            self.assertTrue((snapshots_dir / "index.json").exists())
            self.assertTrue(Path(snap.archive_path).exists())
            self.assertTrue(any(record.id == snap.id for record in manager.list()))


if __name__ == "__main__":
    unittest.main()
