from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.custom.messaging_bridge_admin import TOOL_SPEC, run


class MessagingBridgeAdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "messaging_bridge_admin")

    def test_status(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = run({"action": "status"}, self.ctx)
        self.assertIn("telegram_enabled", result)
        self.assertIn("twilio_enabled", result)

    def test_send_telegram_missing_token(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = run({"action": "send_telegram", "chat_id": "1", "text": "x"}, self.ctx)
        self.assertIn("error", result)

    def test_send_telegram_logs_memory_best_effort(self) -> None:
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "t"}, clear=True):
            with patch("tools.custom.messaging_bridge_admin.telegram_send_message") as send_mock:
                with patch("tools.custom.messaging_bridge_admin.conversation_memory_run", return_value={"ok": True, "entry_id": "e1"}):
                    result = run({"action": "send_telegram", "chat_id": "1", "text": "hello"}, self.ctx)
        self.assertTrue(result["ok"])
        self.assertTrue(result["memory_logged"])
        send_mock.assert_called_once()

    def test_send_telegram_memory_error_does_not_block_send(self) -> None:
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "t"}, clear=True):
            with patch("tools.custom.messaging_bridge_admin.telegram_send_message") as send_mock:
                with patch("tools.custom.messaging_bridge_admin.conversation_memory_run", return_value={"error": "boom"}):
                    result = run({"action": "send_telegram", "chat_id": "1", "text": "hello"}, self.ctx)
        self.assertTrue(result["ok"])
        self.assertFalse(result["memory_logged"])
        self.assertIn("memory_error", result)
        send_mock.assert_called_once()

    def test_send_sms_success(self) -> None:
        env = {
            "TWILIO_ACCOUNT_SID": "sid",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_FROM_NUMBER": "+1000",
        }
        with patch.dict("os.environ", env, clear=True):
            with patch("tools.custom.messaging_bridge_admin.twilio_send_sms") as mocked:
                result = run({"action": "send_sms", "to_number": "+1222", "text": "hello"}, self.ctx)
        self.assertTrue(result["ok"])
        mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
