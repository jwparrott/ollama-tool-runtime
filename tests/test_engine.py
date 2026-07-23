from __future__ import annotations

import unittest
from typing import Any

from agent_runtime.engine import ToolChatEngine


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []
        self.context_windows: list[int] = []

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        context_window_tokens: int,
    ) -> dict[str, Any]:
        _ = model
        _ = tools
        self.calls.append([dict(m) for m in messages])
        self.context_windows.append(context_window_tokens)
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
        self.assertEqual(client.context_windows, [8192, 8192])

    def test_context_window_override(self) -> None:
        client = _FakeClient()
        engine = ToolChatEngine(client=client, registry=_FakeRegistry(), builtin_tools=_FakeBuiltins())
        reply = engine.run(model="fake", user_prompt="hello", context_window_tokens=16384)
        self.assertEqual(reply, "ok")
        self.assertEqual(client.context_windows, [16384])

    def test_tool_keyerror_is_fed_back_not_raised(self) -> None:
        """A KeyError from a tool (e.g. missing required arg) must not crash the engine."""
        tool_call_response = {
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": "bad_tool", "arguments": {}}}],
            }
        }
        final_response = {"message": {"content": "recovered", "tool_calls": []}}
        responses = iter([tool_call_response, final_response])

        class _KeyErrorClient:
            def chat(self, model, messages, tools, context_window_tokens):
                return next(responses)

        class _KeyErrorBuiltins:
            def specs(self):
                return []

            def dispatch(self):
                def _raise(args):
                    raise KeyError("description")
                return {"bad_tool": _raise}

        engine = ToolChatEngine(
            client=_KeyErrorClient(), registry=_FakeRegistry(), builtin_tools=_KeyErrorBuiltins()
        )
        reply = engine.run(model="fake", user_prompt="trigger keyerror")
        self.assertEqual(reply, "recovered")

    def test_tool_value_error_is_fed_back_not_raised(self) -> None:
        """A ValueError from a tool must not crash the engine."""
        tool_call_response = {
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": "bad_tool", "arguments": {}}}],
            }
        }
        final_response = {"message": {"content": "recovered from value error", "tool_calls": []}}
        responses = iter([tool_call_response, final_response])

        class _ValErrClient:
            def chat(self, model, messages, tools, context_window_tokens):
                return next(responses)

        class _ValErrBuiltins:
            def specs(self):
                return []

            def dispatch(self):
                def _raise(args):
                    raise ValueError("missing required field: description")
                return {"bad_tool": _raise}

        engine = ToolChatEngine(
            client=_ValErrClient(), registry=_FakeRegistry(), builtin_tools=_ValErrBuiltins()
        )
        reply = engine.run(model="fake", user_prompt="trigger valueerror")
        self.assertEqual(reply, "recovered from value error")


if __name__ == "__main__":
    unittest.main()
