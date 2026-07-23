from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_runtime.messaging_bridge import MessagingBridgeService


class _FakeEngine:
    def run(self, model, user_prompt, max_steps, context_window_tokens):
        _ = model
        _ = max_steps
        _ = context_window_tokens
        return f"echo:{user_prompt.splitlines()[-1]}"


class MessagingBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _bridge(self):
        return MessagingBridgeService(
            engine=_FakeEngine(),
            model="m",
            project_root=self.root,
            context_window_tokens=4096,
            max_steps=6,
            poll_interval_seconds=1,
        )

    def test_run_once_with_no_env(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            bridge = self._bridge()
            out = bridge.run_once()
        self.assertTrue(out["ok"])
        self.assertFalse(out["telegram"]["enabled"])
        self.assertFalse(out["sms"]["enabled"])

    def test_telegram_poll_processes_text(self) -> None:
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "t"}, clear=True):
            bridge = self._bridge()
            with patch(
                "agent_runtime.messaging_bridge.telegram_get_updates",
                return_value=[{"update_id": 1, "message": {"chat": {"id": 42}, "text": "hello"}}],
            ):
                with patch("agent_runtime.messaging_bridge.telegram_send_message") as sender:
                    result = bridge._poll_telegram_once()
        self.assertTrue(result["enabled"])
        self.assertEqual(result["processed_prompts"], 1)
        self.assertEqual(sender.call_count, 2)
        self.assertEqual(sender.call_args_list[0].kwargs["text"], "Message received. Processing now...")
        self.assertTrue(str(sender.call_args_list[1].kwargs["text"]).startswith("echo:hello"))

    def test_sms_poll_processes_inbound(self) -> None:
        env = {
            "TWILIO_ACCOUNT_SID": "sid",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_FROM_NUMBER": "+1000",
        }
        with patch.dict("os.environ", env, clear=True):
            bridge = self._bridge()
            with patch(
                "agent_runtime.messaging_bridge.twilio_list_messages",
                return_value=[
                    {"sid": "SM1", "direction": "inbound", "from": "+1222", "body": "ping"},
                ],
            ):
                with patch("agent_runtime.messaging_bridge.twilio_send_sms") as sender:
                    result = bridge._poll_twilio_sms_once()
        self.assertTrue(result["enabled"])
        self.assertEqual(result["processed_prompts"], 1)
        sender.assert_called_once()

    def test_telegram_ack_text_can_be_configured(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "t",
            "BRIDGE_TELEGRAM_ACK_TEXT": "Working on it...",
        }
        with patch.dict("os.environ", env, clear=True):
            bridge = self._bridge()
            with patch(
                "agent_runtime.messaging_bridge.telegram_get_updates",
                return_value=[{"update_id": 1, "message": {"chat": {"id": 42}, "text": "hello"}}],
            ):
                with patch("agent_runtime.messaging_bridge.telegram_send_message") as sender:
                    bridge._poll_telegram_once()
        self.assertEqual(sender.call_args_list[0].kwargs["text"], "Working on it...")


if __name__ == "__main__":
    unittest.main()
