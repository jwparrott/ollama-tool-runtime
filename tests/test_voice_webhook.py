from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_runtime.voice_webhook import (
    TwilioVoiceWebhookService,
    _parse_form_encoded,
    _twiml_gather,
    _twiml_say_hangup,
)


class _FakeEngine:
    def run(self, model, user_prompt, max_steps, context_window_tokens):
        _ = model
        _ = max_steps
        _ = context_window_tokens
        if "Conversation so far" in user_prompt:
            return "I heard you clearly."
        return "ok"


class VoiceWebhookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.service = TwilioVoiceWebhookService(
            engine=_FakeEngine(),
            model="demo",
            project_root=self.root,
            context_window_tokens=4096,
            max_steps=6,
            host="127.0.0.1",
            port=8787,
            path_prefix="/voice",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parse_form_encoded(self) -> None:
        parsed = _parse_form_encoded("CallSid=abc&From=%2B123&SpeechResult=hello+there")
        self.assertEqual(parsed["CallSid"], "abc")
        self.assertEqual(parsed["From"], "+123")
        self.assertEqual(parsed["SpeechResult"], "hello there")

    def test_incoming_creates_session_and_returns_gather(self) -> None:
        twiml = self.service._handle_incoming({"CallSid": "CA1", "From": "+1000", "To": "+2000"})
        self.assertIn("<Gather", twiml)
        self.assertIn("CA1", self.service._sessions)

    def test_gather_with_no_speech_reprompts(self) -> None:
        self.service._handle_incoming({"CallSid": "CA2", "From": "+1000", "To": "+2000"})
        twiml = self.service._handle_gather({"CallSid": "CA2"})
        self.assertIn("didn't catch", twiml.lower())
        self.assertIn("<Gather", twiml)

    def test_gather_with_speech_runs_model_and_replies(self) -> None:
        self.service._handle_incoming({"CallSid": "CA3", "From": "+1000", "To": "+2000"})
        twiml = self.service._handle_gather({"CallSid": "CA3", "SpeechResult": "What can you do?"})
        self.assertIn("I heard you clearly", twiml)
        self.assertIn("<Gather", twiml)
        self.assertGreaterEqual(len(self.service._sessions["CA3"].turns), 2)

    def test_turn_limit_hangup(self) -> None:
        self.service.max_turns_per_call = 1
        self.service._handle_incoming({"CallSid": "CA4", "From": "+1000", "To": "+2000"})
        _ = self.service._handle_gather({"CallSid": "CA4", "SpeechResult": "one"})
        twiml = self.service._handle_gather({"CallSid": "CA4", "SpeechResult": "two"})
        self.assertIn("<Hangup/>", twiml)

    def test_twiml_helpers(self) -> None:
        gather = _twiml_gather(
            say_text="Hello <world>",
            action="/voice/gather",
            voice="alice",
            language="en-US",
            finish_on_timeout=True,
        )
        self.assertIn("&lt;world&gt;", gather)
        self.assertIn("speech dtmf", gather)
        hangup = _twiml_say_hangup("Bye & thanks")
        self.assertIn("&amp;", hangup)
        self.assertIn("<Hangup/>", hangup)


if __name__ == "__main__":
    unittest.main()
