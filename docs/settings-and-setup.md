# Settings and First-Run Setup

Settings model is in [agent_runtime/settings.py](../agent_runtime/settings.py).

Persistent settings file:

- `.runtime/settings.json`

## First run

When you run most commands, runtime calls `SettingsManager.ensure_initialized(...)`:

- if settings exist: load and continue
- if no settings and terminal is interactive: run yes/no setup wizard
- if no settings and non-interactive shell: write defaults automatically

## Setup command

Run any time:

```powershell
python main.py setup
```

Questions:
1. Enable voice in GUI?
2. Speak replies by default? (only asked when voice enabled)

## Current settings fields

- `version`: schema version
- `enable_voice_in_gui`: default voice availability
- `speak_replies_by_default`: initial checkbox value in GUI

## Override behavior

Even if voice is enabled in settings, command-line `--no-voice` on `gui` disables it for that run.

