"""Tests for the search_in_files custom tool."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.search_in_files import run, TOOL_SPEC


class SearchInFilesSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "search_in_files")
        self.assertEqual(TOOL_SPEC["parameters"]["required"], ["pattern"])


class SearchInFilesTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, rel_path: str, content: str) -> None:
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def test_basic_match(self):
        self._write("a.txt", "hello world\ngoodbye\n")
        result = run({"pattern": "hello"}, self.ctx)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(result["matches"][0]["content"], "hello world")
        self.assertEqual(result["matches"][0]["line"], 1)

    def test_no_match(self):
        self._write("a.txt", "nothing here\n")
        result = run({"pattern": "NOTFOUND"}, self.ctx)
        self.assertEqual(result["match_count"], 0)

    def test_case_sensitive_by_default(self):
        self._write("a.txt", "Hello World\n")
        result = run({"pattern": "hello"}, self.ctx)
        self.assertEqual(result["match_count"], 0)

    def test_case_insensitive_flag(self):
        self._write("a.txt", "Hello World\n")
        result = run({"pattern": "hello", "case_insensitive": True}, self.ctx)
        self.assertEqual(result["match_count"], 1)

    def test_glob_pattern_filters_files(self):
        self._write("code.py", "import os\n")
        self._write("readme.md", "import os\n")
        result = run({"pattern": "import os", "glob_pattern": "**/*.py"}, self.ctx)
        files = [m["file"] for m in result["matches"]]
        self.assertTrue(all(f.endswith(".py") for f in files))
        self.assertFalse(any(f.endswith(".md") for f in files))

    def test_context_lines_included(self):
        self._write("f.txt", "line1\nTARGET\nline3\n")
        result = run({"pattern": "TARGET", "context_lines": 1}, self.ctx)
        m = result["matches"][0]
        self.assertEqual(m["context_before"], ["line1"])
        self.assertEqual(m["context_after"], ["line3"])

    def test_skips_pycache(self):
        self._write("__pycache__/cached.pyc", "match_this")
        result = run({"pattern": "match_this"}, self.ctx)
        self.assertEqual(result["match_count"], 0)

    def test_multiple_files_multiple_matches(self):
        self._write("a.txt", "foo\nfoo\n")
        self._write("b.txt", "foo\n")
        result = run({"pattern": "foo"}, self.ctx)
        self.assertEqual(result["match_count"], 3)

    def test_invalid_regex_returns_error(self):
        result = run({"pattern": "["}, self.ctx)
        self.assertIn("error", result)

    def test_max_matches_truncates(self):
        self._write("f.txt", "\n".join(["match"] * 20))
        result = run({"pattern": "match", "max_matches": 5}, self.ctx)
        self.assertEqual(len(result["matches"]), 5)
        self.assertTrue(result["truncated"])

    def test_file_and_line_reported(self):
        self._write("sub/code.py", "x = 1\ny = FIND_ME\n")
        result = run({"pattern": "FIND_ME"}, self.ctx)
        m = result["matches"][0]
        self.assertIn("sub", m["file"])
        self.assertEqual(m["line"], 2)


if __name__ == "__main__":
    unittest.main()
