from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.custom.conversation_memory import TOOL_SPEC, run


class ConversationMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = {"project_root": str(self.root)}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "conversation_memory")

    def test_log_turn_and_query(self) -> None:
        saved = run(
            {
                "action": "log_turn",
                "session_id": "s1",
                "role": "assistant",
                "content": "Use tests before commit",
                "intent": "workflow advice",
                "decision": "run-tests",
                "outcome": "tests passed",
                "tags": ["testing", "quality"],
            },
            self.ctx,
        )
        self.assertTrue(saved.get("ok"))

        queried = run({"action": "query_history", "query": "tests", "limit": 5}, self.ctx)
        self.assertGreaterEqual(queried.get("result_count", 0), 1)
        self.assertIn("entries", queried)

    def test_add_feedback_positive_and_negative(self) -> None:
        first = run(
            {
                "action": "log_turn",
                "session_id": "s2",
                "content": "Use parser A",
                "decision": "parser A",
                "outcome": "worked well",
            },
            self.ctx,
        )
        second = run(
            {
                "action": "log_turn",
                "session_id": "s2",
                "content": "Use parser B",
                "decision": "parser B",
                "outcome": "failed on noisy input",
            },
            self.ctx,
        )
        self.assertTrue(first.get("ok"))
        self.assertTrue(second.get("ok"))

        up1 = run(
            {"action": "add_feedback", "entry_id": first["entry_id"], "feedback": "positive"},
            self.ctx,
        )
        up2 = run(
            {"action": "add_feedback", "entry_id": second["entry_id"], "feedback": "negative"},
            self.ctx,
        )
        self.assertTrue(up1.get("ok"))
        self.assertTrue(up2.get("ok"))

        ctx = run({"action": "decision_context", "query": "parser", "limit": 10}, self.ctx)
        self.assertEqual(ctx.get("positive_count"), 1)
        self.assertEqual(ctx.get("negative_count"), 1)
        self.assertIn("parser A", ctx.get("recommended_actions", []))
        self.assertIn("parser B", ctx.get("cautions", []))

    def test_list_sessions(self) -> None:
        run({"action": "log_turn", "session_id": "alpha", "content": "a"}, self.ctx)
        run({"action": "log_turn", "session_id": "beta", "content": "b"}, self.ctx)
        result = run({"action": "list_sessions"}, self.ctx)
        self.assertEqual(result.get("session_count"), 2)


if __name__ == "__main__":
    unittest.main()
