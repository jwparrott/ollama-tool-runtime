# Fresh System Install Scripts

This repository includes interactive bootstrap scripts for new Windows or Linux systems.

## Scripts

- Windows PowerShell: [scripts/install_configure_windows.ps1](../scripts/install_configure_windows.ps1)
- Linux Bash: [scripts/install_configure_linux.sh](../scripts/install_configure_linux.sh)

## What these scripts do

1. Install required dependencies (Git, Python, Ollama) when missing.
2. Ask yes/no questions for optional voice dependencies.
3. Ask whether to download a model now (`ollama pull`).
4. Show a numbered list of common models and allow manual model name entry.
5. Ask for context window token size.
6. Write runtime settings to `.runtime/settings.json`.
7. Start Ollama service/process.
8. Run project tests.
9. Optionally launch the GUI immediately.

## Model selection behavior

Both scripts present a numbered list:

1. `llama3.1:8b`
2. `llama3.1:70b`
3. `qwen2.5:7b`
4. `mistral:7b`
5. Manual model name entry

You select by typing the number.

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

