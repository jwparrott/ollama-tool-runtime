"""Tests for the read_file custom tool."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.read_file import run, TOOL_SPEC


class ReadFileSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "read_file")
        self.assertEqual(TOOL_SPEC["parameters"]["required"], ["path"])

    def test_spec_has_optional_line_params(self):
        props = TOOL_SPEC["parameters"]["properties"]
        self.assertIn("start_line", props)
        self.assertIn("end_line", props)


class ReadFileTests(unittest.TestCase):
    def setUp(self):
        import tempfile
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

    def test_read_full_file(self):
        self._write("hello.txt", "line one\nline two\nline three\n")
        result = run({"path": "hello.txt"}, self.ctx)
        self.assertNotIn("error", result)
        self.assertIn("line one", result["content"])
        self.assertIn("line two", result["content"])
        self.assertEqual(result["total_lines"], 3)

    def test_read_line_range(self):
        self._write("data.txt", "a\nb\nc\nd\ne\n")
        result = run({"path": "data.txt", "start_line": 2, "end_line": 4}, self.ctx)
        self.assertNotIn("error", result)
        self.assertIn("b", result["content"])
        self.assertIn("d", result["content"])
        self.assertNotIn("a\n", result["content"])  # line 1 excluded
        self.assertEqual(result["returned_lines"], "2-4")

    def test_line_numbers_prefixed(self):
        self._write("nums.txt", "x\ny\n")
        result = run({"path": "nums.txt"}, self.ctx)
        self.assertIn("1.", result["content"])
        self.assertIn("2.", result["content"])

    def test_file_not_found(self):
        result = run({"path": "missing.txt"}, self.ctx)
        self.assertIn("error", result)

    def test_path_outside_root_rejected(self):
        result = run({"path": "../../etc/passwd"}, self.ctx)
        self.assertIn("error", result)

    def test_absolute_path_inside_root(self):
        p = self._write("sub/file.txt", "hello\n")
        result = run({"path": str(p)}, self.ctx)
        self.assertNotIn("error", result)
        self.assertIn("hello", result["content"])

    def test_absolute_path_outside_root_rejected(self):
        result = run({"path": "C:/Windows/System32/drivers/etc/hosts"}, self.ctx)
        self.assertIn("error", result)

    def test_directory_returns_entries(self):
        self._write("subdir/a.txt", "a")
        self._write("subdir/b.txt", "b")
        result = run({"path": "subdir"}, self.ctx)
        self.assertEqual(result["type"], "directory")
        self.assertIn("subdir\\a.txt", result["entries"])

    def test_start_line_beyond_eof(self):
        self._write("short.txt", "only one line\n")
        result = run({"path": "short.txt", "start_line": 99}, self.ctx)
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
