"""Tests for the find_files custom tool."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.find_files import run, TOOL_SPEC


class FindFilesSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "find_files")
        self.assertEqual(TOOL_SPEC["parameters"]["required"], ["pattern"])


class FindFilesTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, rel_path: str) -> None:
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")

    def test_find_by_extension(self):
        self._write("a.py")
        self._write("b.py")
        self._write("c.txt")
        result = run({"pattern": "*.py"}, self.ctx)
        self.assertNotIn("error", result)
        names = [Path(m).name for m in result["matches"]]
        self.assertIn("a.py", names)
        self.assertIn("b.py", names)
        self.assertNotIn("c.txt", names)

    def test_recursive_glob(self):
        self._write("src/foo.py")
        self._write("src/sub/bar.py")
        self._write("other.txt")
        result = run({"pattern": "**/*.py"}, self.ctx)
        names = [Path(m).name for m in result["matches"]]
        self.assertIn("foo.py", names)
        self.assertIn("bar.py", names)
        self.assertNotIn("other.txt", names)

    def test_base_path_restricts_search(self):
        self._write("src/a.py")
        self._write("tests/b.py")
        result = run({"pattern": "*.py", "base_path": "src"}, self.ctx)
        names = [Path(m).name for m in result["matches"]]
        self.assertIn("a.py", names)
        self.assertNotIn("b.py", names)

    def test_skips_pycache(self):
        self._write("__pycache__/cached.pyc")
        self._write("real.py")
        result = run({"pattern": "**/*.py*"}, self.ctx)
        paths = result["matches"]
        self.assertFalse(any("__pycache__" in p for p in paths))

    def test_include_dirs_false_by_default(self):
        self._write("mydir/file.txt")
        result = run({"pattern": "mydir"}, self.ctx)
        self.assertEqual(result["matches"], [])

    def test_include_dirs_true(self):
        self._write("mydir/file.txt")
        result = run({"pattern": "mydir", "include_dirs": True}, self.ctx)
        self.assertTrue(any("mydir" in m for m in result["matches"]))

    def test_no_matches_returns_empty(self):
        result = run({"pattern": "*.nonexistent"}, self.ctx)
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["result_count"], 0)

    def test_base_path_outside_root_rejected(self):
        result = run({"pattern": "*.py", "base_path": "../../etc"}, self.ctx)
        self.assertIn("error", result)

    def test_max_results_truncates(self):
        for i in range(10):
            self._write(f"file{i}.txt")
        result = run({"pattern": "*.txt", "max_results": 3}, self.ctx)
        self.assertEqual(len(result["matches"]), 3)
        self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
