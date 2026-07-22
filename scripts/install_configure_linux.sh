#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

step() {
  echo
  echo "==> $1"
}

ask_yes_no() {
  local question="$1"
  local default_yes="${2:-yes}"
  local hint="y/N"
  if [[ "$default_yes" == "yes" ]]; then
    hint="Y/n"
  fi
  while true; do
    read -r -p "$question [$hint]: " answer || answer=""
    answer="${answer,,}"
    if [[ -z "$answer" ]]; then
      [[ "$default_yes" == "yes" ]] && return 0 || return 1
    fi
    [[ "$answer" == "y" || "$answer" == "yes" ]] && return 0
    [[ "$answer" == "n" || "$answer" == "no" ]] && return 1
    echo "Please answer yes or no."
  done
}

ask_positive_int() {
  local question="$1"
  local default_value="$2"
  local min_value="${3:-256}"
  while true; do
    read -r -p "$question [default $default_value]: " answer || answer=""
    if [[ -z "$answer" ]]; then
      echo "$default_value"
      return 0
    fi
    if ! [[ "$answer" =~ ^[0-9]+$ ]]; then
      echo "Please enter a number."
      continue
    fi
    if (( answer < min_value )); then
      echo "Value must be at least $min_value."
      continue
    fi
    echo "$answer"
    return 0
  done
}

choose_model() {
  local models=()
  if mapfile -t models < <(cd "$REPO_ROOT" && python3 -m agent_runtime.install_support list-models --limit 5 2>/dev/null); then
    :
  else
    echo "Could not retrieve suggested models from ollama.com. Falling back to built-in suggestions." >&2
    models=(
      "llama3.1"
      "deepseek-r1"
      "nomic-embed-text"
      "llama3.2"
      "gemma3"
    )
  fi
  if (( ${#models[@]} == 0 )); then
    models=(
      "llama3.1"
      "deepseek-r1"
      "nomic-embed-text"
      "llama3.2"
      "gemma3"
    )
  fi
  echo "Choose model to configure:"
  local i
  for i in "${!models[@]}"; do
    printf "  %d. %s\n" "$((i + 1))" "${models[$i]}"
  done
  printf "  %d. Manual model name\n" "$(( ${#models[@]} + 1 ))"

  while true; do
    read -r -p "Select number [default 1] (1-$(( ${#models[@]} + 1 ))): " choice || choice=""
    if [[ -z "$choice" ]]; then
      echo "${models[0]}"
      return 0
    fi
    if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
      echo "Please enter a number."
      continue
    fi
    if (( choice >= 1 && choice <= ${#models[@]} )); then
      echo "${models[$((choice - 1))]}"
      return 0
    fi
    if (( choice == ${#models[@]} + 1 )); then
      read -r -p "Enter model name (example: llama3.1:8b): " manual || manual=""
      if [[ -z "$manual" ]]; then
        echo "Model name cannot be blank."
        continue
      fi
      local resolved=""
      if resolved="$(printf '%s\n' "$manual" | (cd "$REPO_ROOT" && python3 -m agent_runtime.install_support resolve-model --limit 5 2>/dev/null))"; then
        resolved="${resolved#"${resolved%%[![:space:]]*}"}"
        resolved="${resolved%"${resolved##*[![:space:]]}"}"
      else
        resolved="$manual"
      fi
      if [[ -n "$resolved" && "$resolved" != "$manual" ]]; then
        echo "Using resolved model name '$resolved'." >&2
      fi
      echo "${resolved:-$manual}"
      return 0
    fi
    echo "Please choose a number between 1 and $(( ${#models[@]} + 1 ))."
  done
}

ollama_available() {
  command -v ollama >/dev/null 2>&1
}

ensure_ollama_available() {
  if ollama_available; then
    return 0
  fi
  echo "Ollama is not available in the current shell yet. Skipping Ollama-specific steps for now." >&2
  echo "If Ollama was just installed, open a new terminal after setup completes and run 'ollama serve' or rerun this script." >&2
  return 1
}

start_ollama_service_if_available() {
  if ! ensure_ollama_available; then
    return 1
  fi
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl enable --now ollama || true
  fi
  if ! pgrep -x ollama >/dev/null 2>&1; then
    nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
    sleep 3
  fi
  return 0
}

install_with_pm() {
  local package="$1"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y "$package"
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y "$package"
    return 0
  fi
  if command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm "$package"
    return 0
  fi
  echo "No supported package manager found (apt-get/dnf/pacman)." >&2
  return 1
}

ensure_cmd() {
  local cmd="$1"
  local install_pkg="$2"
  local display="$3"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "$display already installed."
    return 0
  fi
  if ask_yes_no "Install $display now?" "yes"; then
    install_with_pm "$install_pkg"
  else
    echo "$display is required to continue." >&2
    exit 1
  fi
}

step "Preparing fresh-system setup for Ollama tool runtime"
if [[ ! -f "$REPO_ROOT/main.py" ]]; then
  echo "Expected main.py in repository root. Current REPO_ROOT: $REPO_ROOT" >&2
  exit 1
fi

ensure_cmd "git" "git" "Git"
ensure_cmd "python3" "python3" "Python 3"
ensure_cmd "pip3" "python3-pip" "pip3"
ensure_cmd "curl" "curl" "curl"

if ! command -v ollama >/dev/null 2>&1; then
  if ask_yes_no "Install Ollama now?" "yes"; then
    curl -fsSL https://ollama.com/install.sh | sh
  else
    echo "Ollama is required to continue." >&2
    exit 1
  fi
fi

step "Installing runtime dependencies"
if ask_yes_no "Install optional voice dependencies (pyttsx3, SpeechRecognition, pyaudio)?" "no"; then
  python3 -m pip install --upgrade pip
  python3 -m pip install pyttsx3 SpeechRecognition pyaudio
fi

step "Configuring model and runtime settings"
MODEL_NAME="$(choose_model)"
CONTEXT_WINDOW="$(ask_positive_int "Context window size (tokens)" "8192" "256")"

ENABLE_VOICE=false
SPEAK_REPLIES=false
if ask_yes_no "Enable voice in GUI by default?" "yes"; then
  ENABLE_VOICE=true
  if ask_yes_no "Speak assistant replies by default?" "no"; then
    SPEAK_REPLIES=true
  fi
fi

step "Starting Ollama service"
OLLAMA_READY=false
if start_ollama_service_if_available; then
  OLLAMA_READY=true
fi

if [[ "$OLLAMA_READY" == "true" ]] && ask_yes_no "Pull model '$MODEL_NAME' now?" "yes"; then
  ollama pull "$MODEL_NAME"
fi

mkdir -p "$REPO_ROOT/.runtime"
python3 - <<PY
import json
from pathlib import Path

settings = {
    "version": 1,
    "enable_voice_in_gui": ${ENABLE_VOICE@Q} == "true",
    "speak_replies_by_default": ${SPEAK_REPLIES@Q} == "true",
    "default_model": ${MODEL_NAME@Q},
    "context_window_tokens": int(${CONTEXT_WINDOW}),
}
path = Path(${REPO_ROOT@Q}) / ".runtime" / "settings.json"
path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
print(f"Saved settings to {path}")
PY

step "Running tests"
(cd "$REPO_ROOT" && python3 -m unittest discover -s tests)

if ask_yes_no "Launch GUI now?" "yes"; then
  if ensure_ollama_available; then
    NO_VOICE_ARG=""
    if [[ "$ENABLE_VOICE" != "true" ]]; then
      NO_VOICE_ARG="--no-voice"
    fi
    (cd "$REPO_ROOT" && python3 main.py gui --model "$MODEL_NAME" --context-window "$CONTEXT_WINDOW" $NO_VOICE_ARG)
  else
    echo "Skipping GUI launch because Ollama is not available in the current shell." >&2
  fi
fi

step "Setup complete"
echo "You can rerun this script anytime to reconfigure model/context/settings."
