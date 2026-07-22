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
  local models=(
    "llama3.1:8b"
    "llama3.1:70b"
    "qwen2.5:7b"
    "mistral:7b"
  )
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
      echo "$manual"
      return 0
    fi
    echo "Please choose a number between 1 and $(( ${#models[@]} + 1 ))."
  done
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

if ask_yes_no "Pull model '$MODEL_NAME' now?" "yes"; then
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

step "Starting Ollama service"
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl enable --now ollama || true
fi
if ! pgrep -x ollama >/dev/null 2>&1; then
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  sleep 3
fi

step "Running tests"
(cd "$REPO_ROOT" && python3 -m unittest discover -s tests)

if ask_yes_no "Launch GUI now?" "yes"; then
  NO_VOICE_ARG=""
  if [[ "$ENABLE_VOICE" != "true" ]]; then
    NO_VOICE_ARG="--no-voice"
  fi
  (cd "$REPO_ROOT" && python3 main.py gui --model "$MODEL_NAME" --context-window "$CONTEXT_WINDOW" $NO_VOICE_ARG)
fi

step "Setup complete"
echo "You can rerun this script anytime to reconfigure model/context/settings."
