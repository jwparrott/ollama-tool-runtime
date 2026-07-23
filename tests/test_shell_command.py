"""Tests for the shell_command custom tool."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.custom.shell_command import run, TOOL_SPEC


class ShellCommandSpecTests(unittest.TestCase):
    def test_spec_name_and_required(self):
        self.assertEqual(TOOL_SPEC["name"], "shell_command")
        self.assertEqual(TOOL_SPEC["parameters"]["required"], ["command"])


class ShellCommandTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self):
        self._tmpdir.cleanup()

    def _mock_proc(self, stdout="", stderr="", returncode=0):
        proc = MagicMock()
        proc.stdout = stdout
        proc.stderr = stderr
        proc.returncode = returncode
        return proc

    def test_empty_command_returns_error(self):
        result = run({"command": "   "}, self.ctx)
        self.assertIn("error", result)

    def test_blocked_rm_rf(self):
        result = run({"command": "rm -rf /"}, self.ctx)
        self.assertIn("error", result)
        self.assertIn("blocked", result["error"])

    def test_successful_command(self):
        with patch("subprocess.run", return_value=self._mock_proc(stdout="hello\n")) as mock_run:
            result = run({"command": "echo hello"}, self.ctx)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["stdout"], "hello\n")
        self.assertFalse(result["truncated"])

    def test_stderr_captured(self):
        with patch("subprocess.run", return_value=self._mock_proc(stderr="err\n", returncode=1)):
            result = run({"command": "bad_cmd"}, self.ctx)
        self.assertEqual(result["returncode"], 1)
        self.assertEqual(result["stderr"], "err\n")

    def test_timeout_returns_error(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            result = run({"command": "sleep 999"}, self.ctx)
        self.assertIn("error", result)
        self.assertIn("timed out", result["error"])

    def test_os_error_returns_error(self):
        with patch("subprocess.run", side_effect=OSError("no shell")):
            result = run({"command": "ls"}, self.ctx)
        self.assertIn("error", result)

    def test_timeout_clamped_to_120(self):
        captured = {}
        def fake_run(*a, **kw):
            captured["timeout"] = kw.get("timeout")
            return self._mock_proc()
        with patch("subprocess.run", side_effect=fake_run):
            run({"command": "ls", "timeout": 9999}, self.ctx)
        self.assertEqual(captured["timeout"], 120)

    def test_long_stdout_truncated(self):
        long_out = "x" * 10_000
        with patch("subprocess.run", return_value=self._mock_proc(stdout=long_out)):
            result = run({"command": "big output"}, self.ctx)
        self.assertTrue(result["truncated"])
        self.assertIn("truncated", result["stdout"])

    def test_working_dir_is_project_root(self):
        captured = {}
        def fake_run(*a, **kw):
            captured["cwd"] = kw.get("cwd")
            return self._mock_proc()
        with patch("subprocess.run", side_effect=fake_run):
            run({"command": "pwd"}, self.ctx)
        self.assertEqual(captured["cwd"], str(self.root))


if __name__ == "__main__":
    unittest.main()
