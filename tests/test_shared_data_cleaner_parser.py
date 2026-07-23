from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.custom.shared_data_cleaner_parser import TOOL_SPEC, run


class SharedDataCleanerParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "shared_data_cleaner_parser")

    def test_parse_raw_multi_speaker(self) -> None:
        raw = "\n".join(
            [
                "[00:00:01] Alice: Hi Bob",
                "[00:00:03] Bob: Hey Alice",
                "[00:00:05] Alice: Can you review this change?",
            ]
        )
        result = run({"raw_text": raw, "speaker_mode": "multi"}, self.ctx)
        self.assertEqual(result.get("turn_count"), 3)
        self.assertEqual(result["turns"][0]["speaker"], "Alice")
        self.assertEqual(result["turns"][1]["speaker"], "Bob")
        self.assertTrue(result.get("dialogue_pairs"))

    def test_parse_single_speaker_mode(self) -> None:
        raw = "line one\nline two"
        result = run({"raw_text": raw, "speaker_mode": "single"}, self.ctx)
        self.assertEqual(result.get("speaker_count"), 1)
        self.assertEqual(result["turns"][0]["speaker"], "Speaker_1")

    def test_merge_consecutive_turns(self) -> None:
        raw = "Alice: First\nAlice: Second\nBob: Third"
        result = run({"raw_text": raw, "speaker_mode": "multi", "merge_consecutive_turns": True}, self.ctx)
        self.assertEqual(result.get("turn_count"), 2)
        self.assertIn("First Second", result["turns"][0]["text"])

    def test_read_local_file_source(self) -> None:
        transcript = self.root / "transcript.txt"
        transcript.write_text("Sam: hello\nPat: hi", encoding="utf-8")
        result = run({"sources": ["transcript.txt"], "speaker_mode": "multi"}, self.ctx)
        self.assertEqual(result.get("turn_count"), 2)
        self.assertEqual(result["sources"][0]["ok"], True)

    def test_source_outside_root_rejected(self) -> None:
        result = run({"sources": ["../../secret.txt"]}, self.ctx)
        self.assertIn("error", result)

    def test_url_source(self) -> None:
        response = MagicMock()
        response.read.return_value = b"Alice: hello\nBob: hi"
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=response):
            result = run({"sources": ["https://example.com/transcript.txt"], "speaker_mode": "multi"}, self.ctx)
        self.assertEqual(result.get("turn_count"), 2)
        self.assertTrue(result["sources"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
