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

## Internet-backed tools currently included

These tools provide real-time data and are registered in [tools/registry.json](../tools/registry.json):

- `web_search`: DuckDuckGo search (text/news).
- `wikipedia_search`: Wikipedia lookup via MediaWiki API.
- `weather_forecast`: weather via Open-Meteo geocoding + forecast APIs.
- `hackernews_top`: top stories via Hacker News Firebase API.
- `conversation_memory`: persistent chat/decision log with positive or negative reinforcement feedback.
- `shared_data_cleaner_parser`: ingest/clean text from shared sources and parse transcript-style single or multi-speaker turns.
- `pinecone_vector_store`: Pinecone status/upsert/query integration with optional index bootstrap.
- `haystack_rag`: lightweight Haystack ingest/query retrieval tool.
- `browser_automation`: rendered-page extraction through Playwright or Selenium.
- `firecrawl_client`: Firecrawl scrape/crawl/map API integration.
- `web_data_pipeline`: unified web entry point that delegates to search/fetch/scrape to reduce overlap.

## Redundancy-reduction guidance

Preferred default sequence for web content tasks:

1. Use `web_data_pipeline` first.
2. Use `browser_automation` only when dynamic rendering is required.
3. Use `firecrawl_client` for structured crawl/scrape jobs.
