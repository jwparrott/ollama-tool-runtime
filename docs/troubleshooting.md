# Troubleshooting

## Cannot connect to Ollama

Symptom:
- runtime errors mentioning `Cannot connect to Ollama`

Checks:
1. Ensure Ollama service is running.
2. Confirm URL in [agent_runtime/config.py](../agent_runtime/config.py) (`ollama_url`).
3. Confirm selected model is installed.

## Model does not call tools

Possible causes:
- prompt does not require external actions
- model choice has weaker tool-calling behavior
- malformed custom tool specs

Try:
- ask explicitly: “Use available tools to…”
- run `python main.py list-tools` to verify registry visibility

## GUI voice buttons do not work

Likely causes:
- missing dependencies (`pyttsx3`, `SpeechRecognition`, `pyaudio`)
- microphone not accessible
- settings disable voice

Fixes:
1. Install voice dependencies.
2. Run `python main.py setup` and enable voice.
3. Start GUI without `--no-voice`.

## Setup wizard input issues

If stdin closes or is unavailable, setup falls back to defaults instead of crashing.

You can always re-run:

```powershell
python main.py setup
```

## Update rolled back unexpectedly

This usually means tests failed after a file update. Inspect output from:

```powershell
python main.py run-tests
```

and resolve failures before retrying updates.

