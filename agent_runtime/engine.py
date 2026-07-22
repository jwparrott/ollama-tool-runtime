from __future__ import annotations

import json
from typing import Any

from agent_runtime.builtin_tools import BuiltinTools
from agent_runtime.ollama_client import OllamaClient
from agent_runtime.tool_registry import ToolRegistry


SYSTEM_PROMPT = (
    "You are an autonomous development assistant with tool use. "
    "Use tools when needed, especially tests and rollback for risky changes."
)


class ToolChatSession:
    def __init__(self, engine: ToolChatEngine, model: str, context_window_tokens: int) -> None:
        self._engine = engine
        self._model = model
        self._context_window_tokens = context_window_tokens
        self._messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(self, user_prompt: str, max_steps: int = 12) -> str:
        self._messages.append({"role": "user", "content": user_prompt})
        return self._engine.run_with_messages(
            model=self._model,
            messages=self._messages,
            max_steps=max_steps,
            context_window_tokens=self._context_window_tokens,
        )


class ToolChatEngine:
    def __init__(
        self,
        client: OllamaClient,
        registry: ToolRegistry,
        builtin_tools: BuiltinTools,
        default_context_window_tokens: int = 8192,
    ) -> None:
        self.client = client
        self.registry = registry
        self.builtin_tools = builtin_tools
        self.default_context_window_tokens = default_context_window_tokens

    def _all_tool_specs(self) -> list[dict[str, Any]]:
        return self.builtin_tools.specs() + self.registry.get_specs()

    def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        builtins = self.builtin_tools.dispatch()
        if name in builtins:
            return builtins[name](args)
        tool_fn = self.registry.get_callable(name)
        return tool_fn(args, {"runtime": "ollama-tool-runtime"})

    def run_with_messages(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_steps: int = 12,
        context_window_tokens: int | None = None,
    ) -> str:
        tools = self._all_tool_specs()
        resolved_context_window_tokens = context_window_tokens or self.default_context_window_tokens

        for _ in range(max_steps):
            response = self.client.chat(
                model=model,
                messages=messages,
                tools=tools,
                context_window_tokens=resolved_context_window_tokens,
            )
            message = response.get("message", {})
            assistant_content = message.get("content", "")
            tool_calls = message.get("tool_calls") or []

            messages.append({"role": "assistant", "content": assistant_content, "tool_calls": tool_calls})

            if not tool_calls:
                return assistant_content

            for call in tool_calls:
                function = call.get("function", {})
                tool_name = function.get("name")
                arguments = function.get("arguments", {})
                if not tool_name:
                    raise RuntimeError("Received tool call without function.name.")
                if isinstance(arguments, str):
                    parsed_args = json.loads(arguments or "{}")
                else:
                    if not isinstance(arguments, dict):
                        raise RuntimeError(f"Tool arguments for '{tool_name}' must be object or JSON string.")
                    parsed_args = arguments
                result = self._execute_tool(str(tool_name), parsed_args)
                messages.append(
                    {
                        "role": "tool",
                        "name": str(tool_name),
                        "tool_name": str(tool_name),
                        "content": json.dumps(result),
                    }
                )

        return "Stopped after max_steps without final response."

    def run(
        self,
        model: str,
        user_prompt: str,
        max_steps: int = 12,
        context_window_tokens: int | None = None,
    ) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return self.run_with_messages(
            model=model,
            messages=messages,
            max_steps=max_steps,
            context_window_tokens=context_window_tokens,
        )

    def start_session(self, model: str, context_window_tokens: int | None = None) -> ToolChatSession:
        return ToolChatSession(
            engine=self,
            model=model,
            context_window_tokens=context_window_tokens or self.default_context_window_tokens,
        )
