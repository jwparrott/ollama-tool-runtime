# Ollama Tool Runtime with Self-Update Safety

This project provides a local runtime that lets an Ollama-hosted LLM call tools, add new tools, and safely update this codebase with automated test gates and rollback snapshots.

## Full documentation

For complete command, architecture, function, and operations documentation, start at:

- [docs/README.md](./docs/README.md)

For fresh Windows/Linux bootstrap scripts (install + configure + model pull), see:

- [docs/install-scripts.md](./docs/install-scripts.md)

## What it does

- Runs a tool-enabled chat loop against local Ollama.
- Loads custom tools from a registry-backed plugin folder.
- Exposes built-in workflow skills (`list_model_skills`, `get_model_skill`) to guide the model through repeatable engineering tasks.
- Exposes built-in admin tools so the model can:
  - register new tools,
  - update files in this project,
  - run tests,
  - snapshot and rollback.
- Automatically restores the previous snapshot if a self-update fails tests.

## Project layout

- `main.py`: CLI entrypoint
- `agent_runtime/`: runtime implementation
- `tools/custom/`: user/custom tools
- `tools/registry.json`: tool registration data
- `scripts/`: fresh-system install/configuration scripts
- `.runtime/snapshots/`: generated rollback snapshots
- `tests/`: unit tests

## Requirements

- Python 3.10+
- Local Ollama server running at `http://127.0.0.1:11434`
- For voice features in GUI: `pip install pyttsx3 SpeechRecognition pyaudio`

## Quick start

```powershell
python -m unittest discover -s tests
bash ./scripts/install_configure_linux.sh
python main.py setup
python main.py list-tools
python main.py chat --model llama3.1 --prompt "List the tools you can use."
python main.py chat-interactive --model llama3.1
python main.py gui --model llama3.1
python main.py gui --model llama3.1 --no-voice
```

## CLI usage

```powershell
python main.py chat --model llama3.1 --prompt "Hello"
python main.py chat-interactive --max-steps 12
python main.py gui --max-steps 12
python main.py gui --model llama3.1 --no-voice
python main.py setup
python main.py list-tools
python main.py snapshot --note "manual checkpoint"
python main.py rollback --id <snapshot-id>
python main.py run-tests
```

## Setup wizard

- On first run, the runtime starts an interactive yes/no setup wizard and stores feature flags in `.runtime/settings.json`.
- On later runs, your saved settings are reused.
- If stdin closes unexpectedly (for example, some automated shells), setup now falls back to the default answer for each question instead of crashing.
- To change feature flags later, run:

```powershell
python main.py setup
```

## Installer scripts

- The bootstrap scripts in `scripts/` fetch the current popular model suggestions from Ollama's library page instead of using a stale hardcoded list.
- Manual model entry accepts common near-matches such as `gemma 3` or `deepseek r1 7b` and resolves them to canonical Ollama model names when possible.
- Ollama-specific steps such as `ollama pull` are skipped when the `ollama` command is not yet available in the current shell after installation.

## Real-time internet tools

This runtime now includes internet-backed tools for current information:

- `web_search` (DuckDuckGo)
- `wikipedia_search` (MediaWiki API)
- `weather_forecast` (Open-Meteo)
- `hackernews_top` (Hacker News API)

It also includes conversation-learning and transcript tooling:

- `conversation_memory` for persistent chat history, decision logs, and positive/negative user feedback reinforcement
- `shared_data_cleaner_parser` for collecting/cleaning unstructured text from files/URLs and parsing multi-speaker conversations

### Integration tools (optional dependencies)

The runtime can also integrate with external platforms when their SDKs/keys are available:

- `pinecone_vector_store` (Pinecone vector DB)
- `haystack_rag` (Haystack ingestion/retrieval)
- `browser_automation` (Playwright/Selenium rendered-page extraction)
- `firecrawl_client` (Firecrawl scrape/crawl/map API)

To reduce redundant web workflows, use `web_data_pipeline` as the default unified entry point for:

- web search
- URL fetch
- scrape delegation

## How self-update safety works

1. Before applying updates, the runtime creates a snapshot zip.
2. It writes requested file changes.
3. It runs tests (default: `python -m unittest discover -s tests`).
4. If tests fail, it automatically restores the previous snapshot.

This prevents a bad update from permanently breaking the runtime.
