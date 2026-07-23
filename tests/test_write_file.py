"""Tests for the write_file custom tool."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.write_file import run, TOOL_SPEC


class WriteFileSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "write_file")
        self.assertCountEqual(TOOL_SPEC["parameters"]["required"], ["path", "content"])


class WriteFileTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_create_new_file(self):
        result = run({"path": "new.txt", "content": "hello world"}, self.ctx)
        self.assertTrue(result.get("ok"))
        self.assertEqual((self.root / "new.txt").read_text(encoding="utf-8"), "hello world")
        self.assertTrue(result.get("created"))
        self.assertFalse(result.get("overwritten"))

    def test_creates_parent_dirs(self):
        result = run({"path": "a/b/c.txt", "content": "deep"}, self.ctx)
        self.assertTrue(result.get("ok"))
        self.assertTrue((self.root / "a" / "b" / "c.txt").exists())

    def test_overwrite_false_blocks_existing(self):
        (self.root / "existing.txt").write_text("old", encoding="utf-8")
        result = run({"path": "existing.txt", "content": "new"}, self.ctx)
        self.assertIn("error", result)
        self.assertEqual((self.root / "existing.txt").read_text(encoding="utf-8"), "old")

    def test_overwrite_true_replaces_file(self):
        (self.root / "existing.txt").write_text("old", encoding="utf-8")
        result = run({"path": "existing.txt", "content": "new", "overwrite": True}, self.ctx)
        self.assertTrue(result.get("ok"))
        self.assertEqual((self.root / "existing.txt").read_text(encoding="utf-8"), "new")
        self.assertFalse(result.get("created"))
        self.assertTrue(result.get("overwritten"))

    def test_path_outside_root_rejected(self):
        result = run({"path": "../../evil.txt", "content": "bad"}, self.ctx)
        self.assertIn("error", result)

    def test_path_is_directory_rejected(self):
        (self.root / "adir").mkdir()
        result = run({"path": "adir", "content": "x"}, self.ctx)
        self.assertIn("error", result)

    def test_bytes_written_reported(self):
        result = run({"path": "bytes.txt", "content": "abc"}, self.ctx)
        self.assertEqual(result["bytes_written"], 3)

    def test_relative_path_returned(self):
        result = run({"path": "sub/out.txt", "content": "x"}, self.ctx)
        self.assertIn("sub", result["path"])


if __name__ == "__main__":
    unittest.main()
