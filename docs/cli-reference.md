# CLI Command Reference

Command runner: [main.py](../main.py)

## `setup`

Runs the interactive yes/no setup wizard and writes settings to `.runtime/settings.json`.

```powershell
python main.py setup
```

Use when:
- first-time configuration
- changing feature toggles later

## `chat`

Runs a single tool-enabled chat turn.

```powershell
python main.py chat --model llama3.1 --prompt "Hello"
python main.py chat --prompt "Hello"  # uses configured default model
```

Arguments:
- `--model` (required): Ollama model name
- `--model` (optional): Ollama model name (defaults to configured setting)
- `--context-window` (optional): context window tokens (defaults to configured setting)
- `--prompt` (required): one prompt

Use when:
- scripting
- quick one-shot requests

## `chat-interactive`

Runs a multi-turn terminal REPL chat.

```powershell
python main.py chat-interactive --model llama3.1 --max-steps 12
python main.py chat-interactive --max-steps 12
```

Arguments:
- `--model` (optional, uses configured default when omitted)
- `--context-window` (optional, uses configured default when omitted)
- `--max-steps` (optional, default `12`): max tool loop iterations per turn

Exit with:
- `exit`
- `quit`
- `Ctrl+C` / `Ctrl+D`

## `gui`

Runs desktop chat UI.

```powershell
python main.py gui --model llama3.1 --max-steps 12
python main.py gui --max-steps 12
python main.py gui --model llama3.1 --no-voice
```

Arguments:
- `--model` (optional, uses configured default when omitted)
- `--context-window` (optional, uses configured default when omitted)
- `--max-steps` (optional, default `12`)
- `--no-voice` (optional): force-disable STT/TTS even if enabled in settings

## `list-tools`

Prints built-in and custom tool metadata.

```powershell
python main.py list-tools
```

## `snapshot`

Creates a manual rollback snapshot.

```powershell
python main.py snapshot --note "before-change"
```

## `rollback`

Restores project files to a previous snapshot.

```powershell
python main.py rollback --id 20260721123456000000
```

## `run-tests`

Runs default tests or custom command.

```powershell
python main.py run-tests
python main.py run-tests --test-cmd "python -m unittest discover -s tests"
```

## `bridge-run`

Runs the background messaging bridge that ingests prompts from Telegram and Twilio SMS, sends them through the LLM runtime, and returns responses to the same channel.

```powershell
python main.py bridge-run --model llama3.1
python main.py bridge-run --model llama3.1 --once
```

Arguments:
- `--model` (optional, uses configured default when omitted)
- `--context-window` (optional, uses configured default when omitted)
- `--timeout` (optional): Ollama request timeout
- `--max-steps` (optional, default `12`)
- `--poll-interval` (optional, default `2`)
- `--once` (optional): run one poll cycle then exit

## `voice-webhook-run`

Runs an HTTP webhook server for inbound Twilio voice calls, supports STT (`<Gather input="speech">`) and back-and-forth call conversation.

```powershell
python main.py voice-webhook-run --model llama3.1
python main.py voice-webhook-run --model llama3.1 --host 0.0.0.0 --port 8787 --path-prefix /voice
```

Arguments:
- `--model` (optional, uses configured default when omitted)
- `--context-window` (optional, uses configured default when omitted)
- `--timeout` (optional): Ollama request timeout
- `--max-steps` (optional, default `12`): max tool loop steps per voice turn
- `--host` (optional, default `0.0.0.0`)
- `--port` (optional, default `8787`)
- `--path-prefix` (optional, default `/voice`)
- `--voice` (optional, default `alice`)
- `--language` (optional, default `en-US`)
- `--max-call-turns` (optional, default `12`)
