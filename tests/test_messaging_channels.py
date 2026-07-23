from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from agent_runtime.messaging_channels import (
    telegram_get_updates,
    telegram_send_message,
    twilio_list_messages,
    twilio_send_sms,
)


class MessagingChannelsTests(unittest.TestCase):
    def _mock_response(self, payload: dict):
        resp = MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_telegram_get_updates(self) -> None:
        payload = {"ok": True, "result": [{"update_id": 1, "message": {"text": "hi"}}]}
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            updates = telegram_get_updates("token", offset=0)
        self.assertEqual(len(updates), 1)

    def test_telegram_send_message(self) -> None:
        payload = {"ok": True, "result": {"message_id": 9}}
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = telegram_send_message("token", chat_id="123", text="hello")
        self.assertTrue(result["ok"])

    def test_twilio_list_messages(self) -> None:
        payload = {"messages": [{"sid": "SM1", "direction": "inbound"}]}
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = twilio_list_messages("sid", "token", to_number="+10000000000")
        self.assertEqual(result[0]["sid"], "SM1")

    def test_twilio_send_sms(self) -> None:
        payload = {"sid": "SMX"}
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = twilio_send_sms("sid", "token", from_number="+1000", to_number="+2000", body="hey")
        self.assertEqual(result["sid"], "SMX")


if __name__ == "__main__":
    unittest.main()
