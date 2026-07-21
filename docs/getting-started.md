# Getting Started

## What this project is

This runtime lets an LLM hosted in Ollama use tools defined by your Python program. It supports:

- tool-calling chat
- custom tool registration
- self-update with test gates
- snapshot + rollback safety
- GUI chat with optional speech input/output

## Requirements

- Python 3.10+
- Ollama running locally (`http://127.0.0.1:11434`)
- Optional voice dependencies:
  - `pyttsx3`
  - `SpeechRecognition`
  - `pyaudio`

## First run

From the repository root:

```powershell
python -m unittest discover -s tests
python main.py setup
```

Then start chatting:

```powershell
python main.py chat --model llama3.1 --prompt "List your tools."
```

## Main entry points

- CLI: [main.py](../main.py)
- Runtime engine: [agent_runtime/engine.py](../agent_runtime/engine.py)
- GUI: [agent_runtime/gui.py](../agent_runtime/gui.py)
- Tool declarations: [tools/registry.json](../tools/registry.json)

