"""Tests for the edit_file custom tool."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.edit_file import run, TOOL_SPEC


class EditFileSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "edit_file")
        self.assertCountEqual(TOOL_SPEC["parameters"]["required"], ["path", "old_str", "new_str"])


class EditFileTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, rel_path: str, content: str) -> Path:
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_basic_replacement(self):
        self._write("f.txt", "foo bar baz")
        result = run({"path": "f.txt", "old_str": "bar", "new_str": "QUX"}, self.ctx)
        self.assertTrue(result.get("ok"))
        self.assertEqual((self.root / "f.txt").read_text(encoding="utf-8"), "foo QUX baz")

    def test_delete_with_empty_new_str(self):
        self._write("f.txt", "hello world")
        result = run({"path": "f.txt", "old_str": " world", "new_str": ""}, self.ctx)
        self.assertTrue(result.get("ok"))
        self.assertEqual((self.root / "f.txt").read_text(encoding="utf-8"), "hello")

    def test_old_str_not_found_returns_error(self):
        self._write("f.txt", "hello")
        result = run({"path": "f.txt", "old_str": "MISSING", "new_str": "x"}, self.ctx)
        self.assertIn("error", result)

    def test_old_str_ambiguous_returns_error(self):
        self._write("f.txt", "abc abc abc")
        result = run({"path": "f.txt", "old_str": "abc", "new_str": "xyz"}, self.ctx)
        self.assertIn("error", result)
        self.assertIn("3", result["error"])

    def test_multiline_replacement(self):
        self._write("f.py", "def foo():\n    return 1\n")
        result = run({"path": "f.py", "old_str": "return 1", "new_str": "return 42"}, self.ctx)
        self.assertTrue(result.get("ok"))
        self.assertIn("return 42", (self.root / "f.py").read_text(encoding="utf-8"))

    def test_file_not_found(self):
        result = run({"path": "no.txt", "old_str": "x", "new_str": "y"}, self.ctx)
        self.assertIn("error", result)

    def test_path_outside_root_rejected(self):
        result = run({"path": "../../etc/passwd", "old_str": "x", "new_str": "y"}, self.ctx)
        self.assertIn("error", result)

    def test_chars_before_after_reported(self):
        self._write("f.txt", "abcde")
        result = run({"path": "f.txt", "old_str": "abc", "new_str": "X"}, self.ctx)
        self.assertEqual(result["chars_before"], 5)
        self.assertEqual(result["chars_after"], 3)  # "Xde"


if __name__ == "__main__":
    unittest.main()
