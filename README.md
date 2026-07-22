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

## How self-update safety works

1. Before applying updates, the runtime creates a snapshot zip.
2. It writes requested file changes.
3. It runs tests (default: `python -m unittest discover -s tests`).
4. If tests fail, it automatically restores the previous snapshot.

This prevents a bad update from permanently breaking the runtime.
