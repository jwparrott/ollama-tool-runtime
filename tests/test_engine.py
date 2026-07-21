from __future__ import annotations

import unittest
from typing import Any

from agent_runtime.engine import ToolChatEngine


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    def chat(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        _ = model
        _ = tools
        self.calls.append([dict(m) for m in messages])
        return {"message": {"content": "ok", "tool_calls": []}}


class _FakeRegistry:
    def get_specs(self) -> list[dict[str, Any]]:
        return []

    def get_callable(self, name: str):
        raise KeyError(name)


class _FakeBuiltins:
    def specs(self) -> list[dict[str, Any]]:
        return []

    def dispatch(self):
        return {}


class EngineTests(unittest.TestCase):
    def test_run_single_turn(self) -> None:
        engine = ToolChatEngine(client=_FakeClient(), registry=_FakeRegistry(), builtin_tools=_FakeBuiltins())
        reply = engine.run(model="fake", user_prompt="hello")
        self.assertEqual(reply, "ok")

    def test_interactive_session_keeps_history(self) -> None:
        client = _FakeClient()
        engine = ToolChatEngine(client=client, registry=_FakeRegistry(), builtin_tools=_FakeBuiltins())
        session = engine.start_session("fake")

        first = session.ask("turn one")
        second = session.ask("turn two")

        self.assertEqual(first, "ok")
        self.assertEqual(second, "ok")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0][0]["role"], "system")
        self.assertEqual(client.calls[0][1]["content"], "turn one")
        self.assertEqual(client.calls[1][-1]["content"], "turn two")
        self.assertTrue(any(msg.get("role") == "assistant" for msg in client.calls[1]))


if __name__ == "__main__":
    unittest.main()

