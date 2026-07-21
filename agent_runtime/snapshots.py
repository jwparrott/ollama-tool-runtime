from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SnapshotRecord:
    id: str
    created_at: str
    note: str
    archive_path: str


class SnapshotManager:
    def __init__(self, project_root: Path, snapshots_dir: Path) -> None:
        self.project_root = project_root
        self.snapshots_dir = snapshots_dir
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.snapshots_dir / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text("[]", encoding="utf-8")

    def _load_index(self) -> list[SnapshotRecord]:
        raw = json.loads(self.index_path.read_text(encoding="utf-8") or "[]")
        return [SnapshotRecord(**item) for item in raw]

    def _save_index(self, records: list[SnapshotRecord]) -> None:
        payload = [record.__dict__ for record in records]
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def create(self, note: str) -> SnapshotRecord:
        now = datetime.now(tz=timezone.utc)
        snapshot_id = now.strftime("%Y%m%d%H%M%S%f")
        base_name = self.snapshots_dir / f"snapshot-{snapshot_id}"
        with tempfile.TemporaryDirectory() as td:
            staging_root = Path(td) / "staging"
            shutil.copytree(
                self.project_root,
                staging_root,
                ignore=shutil.ignore_patterns(".runtime", "__pycache__", "*.pyc"),
            )
            archive_path = shutil.make_archive(str(base_name), "zip", root_dir=staging_root)
        record = SnapshotRecord(
            id=snapshot_id,
            created_at=now.isoformat(),
            note=note,
            archive_path=archive_path,
        )
        records = self._load_index()
        records.append(record)
        self._save_index(records)
        return record

    def list(self) -> list[SnapshotRecord]:
        return self._load_index()

    def restore(self, snapshot_id: str) -> None:
        record = next((r for r in self._load_index() if r.id == snapshot_id), None)
        if record is None:
            raise KeyError(f"Snapshot '{snapshot_id}' not found.")

        archive = Path(record.archive_path)
        if not archive.exists():
            raise FileNotFoundError(f"Snapshot archive not found: {archive}")

        runtime_root = self.snapshots_dir.parent.resolve()
        with tempfile.TemporaryDirectory() as temp_dir:
            unpack_dir = Path(temp_dir) / "restore"
            shutil.unpack_archive(str(archive), str(unpack_dir), "zip")

            for path in self.project_root.iterdir():
                if path.resolve() == runtime_root:
                    continue
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

            for source in unpack_dir.iterdir():
                target = self.project_root / source.name
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
