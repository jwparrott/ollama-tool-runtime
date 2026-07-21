from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_runtime.settings import RuntimeSettings, SettingsManager


class SettingsManagerTests(unittest.TestCase):
    def test_ensure_initialized_non_interactive_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = SettingsManager(Path(td) / ".runtime" / "settings.json")
            settings = manager.ensure_initialized(interactive=False, output_fn=lambda _msg: None)
            self.assertEqual(settings, RuntimeSettings())
            self.assertTrue(manager.settings_path.exists())

    def test_run_setup_updates_settings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = SettingsManager(Path(td) / ".runtime" / "settings.json")
            answers = iter(["n"])
            settings = manager.run_setup(
                input_fn=lambda _prompt: next(answers),
                output_fn=lambda _msg: None,
            )
            self.assertFalse(settings.enable_voice_in_gui)
            self.assertFalse(settings.speak_replies_by_default)

    def test_run_setup_asks_followup_for_speak_replies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = SettingsManager(Path(td) / ".runtime" / "settings.json")
            answers = iter(["y", "y"])
            settings = manager.run_setup(
                input_fn=lambda _prompt: next(answers),
                output_fn=lambda _msg: None,
            )
            self.assertTrue(settings.enable_voice_in_gui)
            self.assertTrue(settings.speak_replies_by_default)

    def test_run_setup_handles_eof_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = SettingsManager(Path(td) / ".runtime" / "settings.json")
            messages: list[str] = []

            def _raise_eof(_prompt: str) -> str:
                raise EOFError()

            settings = manager.run_setup(
                input_fn=_raise_eof,
                output_fn=messages.append,
            )

            self.assertEqual(settings, RuntimeSettings())
            self.assertTrue(any("No input received" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
