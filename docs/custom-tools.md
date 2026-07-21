# Custom Tool Development

Custom tools are loaded from registry entries in [tools/registry.json](../tools/registry.json) and modules under [tools/custom/](../tools/custom/).

Example tool file: [tools/custom/example_echo.py](../tools/custom/example_echo.py)

## Required module contract

Each custom tool module must define:

1. `TOOL_SPEC` dict
2. `run(args, context)` function

Example shape:

```python
TOOL_SPEC = {
    "name": "my_tool",
    "description": "Does X",
    "parameters": {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    },
}

def run(args, context):
    return {"result": args["value"]}
```

## Registration paths

### Option A: via LLM tool (`register_python_tool`)

Ask the model to call built-in registration tool.

### Option B: manually

1. Create `tools/custom/<name>.py`
2. Add entry to [tools/registry.json](../tools/registry.json):

```json
{
  "name": "my_tool",
  "module": "tools.custom.my_tool",
  "enabled": true
}
```

## Runtime loading behavior

- Modules are imported fresh (`ToolRegistry._import_fresh`) so edits can be picked up without restarting process.
- Invalid tool modules are skipped from spec export.
- Missing `run` callable raises runtime error when invoked.

## Good practices

- Keep tool results JSON-serializable.
- Validate incoming args in `run`.
- Keep side effects explicit and small.
- Run `python main.py list-tools` after registration.

