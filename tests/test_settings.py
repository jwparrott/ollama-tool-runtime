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
            answers = iter(["n", "1", "4096"])
            settings = manager.run_setup(
                input_fn=lambda _prompt: next(answers),
                output_fn=lambda _msg: None,
            )
            self.assertFalse(settings.enable_voice_in_gui)
            self.assertFalse(settings.speak_replies_by_default)
            self.assertEqual(settings.default_model, "llama3.1:8b")
            self.assertEqual(settings.context_window_tokens, 4096)

    def test_run_setup_asks_followup_for_speak_replies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = SettingsManager(Path(td) / ".runtime" / "settings.json")
            answers = iter(["y", "y", "2", "12000"])
            settings = manager.run_setup(
                input_fn=lambda _prompt: next(answers),
                output_fn=lambda _msg: None,
            )
            self.assertTrue(settings.enable_voice_in_gui)
            self.assertTrue(settings.speak_replies_by_default)
            self.assertEqual(settings.default_model, "llama3.1:70b")
            self.assertEqual(settings.context_window_tokens, 12000)

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

    def test_run_setup_accepts_manual_model_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = SettingsManager(Path(td) / ".runtime" / "settings.json")
            manual_index = str(len(SettingsManager.COMMON_MODEL_OPTIONS) + 1)
            answers = iter(["n", manual_index, "my-model:latest", "16384"])
            settings = manager.run_setup(
                input_fn=lambda _prompt: next(answers),
                output_fn=lambda _msg: None,
            )
            self.assertEqual(settings.default_model, "my-model:latest")
            self.assertEqual(settings.context_window_tokens, 16384)


if __name__ == "__main__":
    unittest.main()
