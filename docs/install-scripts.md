# Fresh System Install Scripts

This repository includes interactive bootstrap scripts for new Windows or Linux systems.

## Scripts

- Windows PowerShell: [scripts/install_configure_windows.ps1](../scripts/install_configure_windows.ps1)
- Linux Bash: [scripts/install_configure_linux.sh](../scripts/install_configure_linux.sh)

## What these scripts do

1. Install required dependencies (Git, Python, Ollama) when missing.
2. Ask yes/no questions for optional voice dependencies.
3. Ask whether to download a model now (`ollama pull`).
4. Fetch the current popular model suggestions from Ollama's library page and allow manual model name entry.
5. Ask for context window token size.
6. Write runtime settings to `.runtime/settings.json`.
7. Start Ollama service/process.
8. Run project tests.
9. Optionally launch the GUI immediately.

## Model selection behavior

Both scripts fetch the current popular models from `https://ollama.com/library?sort=popular` and present them as a numbered list. If that request fails, they fall back to a built-in list.

The manual entry option also resolves common near-matches against the suggested models, for example:

- `gemma 3` -> `gemma3`
- `deepseek r1 7b` -> `deepseek-r1:7b`

Unknown names are still accepted as entered.

## Ollama availability behavior

- The scripts only run `ollama pull`, start the Ollama service, or launch the GUI when the `ollama` command is actually available in the current shell/session.
- If Ollama was just installed but is not yet on `PATH`, the scripts finish configuration and explain that you may need to open a new terminal and rerun Ollama-specific steps.

## Run on Windows

From repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_configure_windows.ps1
```

## Run on Linux

From repository root:

```bash
bash ./scripts/install_configure_linux.sh
```

## Re-running

These scripts are safe to rerun for reconfiguration and can update model/context/settings on later runs.
