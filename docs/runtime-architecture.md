# How the Runtime Works

Core files:

- [main.py](../main.py)
- [agent_runtime/engine.py](../agent_runtime/engine.py)
- [agent_runtime/ollama_client.py](../agent_runtime/ollama_client.py)
- [agent_runtime/tool_registry.py](../agent_runtime/tool_registry.py)
- [agent_runtime/builtin_tools.py](../agent_runtime/builtin_tools.py)

## Flow overview

1. CLI/GUI starts runtime objects in `build_runtime(...)` from [main.py](../main.py).
2. `ToolChatEngine` sends:
   - message history
   - full tool specs
   - context window (`options.num_ctx`)
   to Ollama via `POST /api/chat`.
3. Model returns either:
   - normal assistant content
   - or `tool_calls`.
4. Engine executes each requested tool:
   - built-in tool dispatch (`BuiltinTools.dispatch`)
   - or custom tool dispatch (`ToolRegistry.get_callable`).
5. Engine appends tool results as `role=tool` messages.
6. Loop continues until model returns final message (or max steps reached).

## Message state

- One-shot mode (`chat`) creates temporary message history.
- Interactive modes (`chat-interactive`, GUI) keep message history in `ToolChatSession`.

## Tool specification shape

Tool specs are sent in Ollama function-tool format:

```json
{
  "type": "function",
  "function": {
    "name": "tool_name",
    "description": "...",
    "parameters": { "type": "object", "properties": {} }
  }
}
```

## Why this design

- Keeps model actions explicit and inspectable through tools.
- Allows controlled extension via registry and module loading.
- Enables self-modification with rollback protections.
