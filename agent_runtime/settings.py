from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class RuntimeSettings:
    version: int = 1
    enable_voice_in_gui: bool = True
    speak_replies_by_default: bool = False
    default_model: str = "llama3.1:8b"
    context_window_tokens: int = 8192


class SettingsManager:
    COMMON_MODEL_OPTIONS: tuple[str, ...] = (
        "llama3.1:8b",
        "llama3.1:70b",
        "qwen2.5:7b",
        "mistral:7b",
    )

    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> RuntimeSettings | None:
        if not self.settings_path.exists():
            return None
        raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        return RuntimeSettings(
            version=int(raw.get("version", 1)),
            enable_voice_in_gui=bool(raw.get("enable_voice_in_gui", True)),
            speak_replies_by_default=bool(raw.get("speak_replies_by_default", False)),
            default_model=str(raw.get("default_model", "llama3.1:8b")),
            context_window_tokens=max(256, int(raw.get("context_window_tokens", 8192))),
        )

    def save(self, settings: RuntimeSettings) -> None:
        self.settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")

    def _ask_yes_no(
        self,
        question: str,
        default: bool,
        input_fn: Callable[[str], str],
        output_fn: Callable[[str], None],
    ) -> bool:
        hint = "Y/n" if default else "y/N"
        while True:
            try:
                answer = input_fn(f"{question} [{hint}]: ").strip().lower()
            except EOFError:
                output_fn(f"No input received for '{question}'. Using default.")
                return default
            if not answer:
                return default
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            output_fn("Please answer yes or no.")

    def _ask_choice(
        self,
        question: str,
        options: tuple[str, ...],
        input_fn: Callable[[str], str],
        output_fn: Callable[[str], None],
        default_index: int = 1,
    ) -> str:
        if default_index < 1 or default_index > len(options):
            raise ValueError("default_index out of range")
        output_fn(question)
        for index, option in enumerate(options, start=1):
            output_fn(f"  {index}. {option}")
        output_fn(f"  {len(options) + 1}. Manual model name")

        while True:
            try:
                answer = input_fn(
                    f"Choose model number [default {default_index}] (1-{len(options) + 1}): "
                ).strip()
            except EOFError:
                output_fn("No input received for model choice. Using default option.")
                return options[default_index - 1]

            if not answer:
                return options[default_index - 1]
            if not answer.isdigit():
                output_fn("Please enter a valid number.")
                continue
            choice = int(answer)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            if choice == len(options) + 1:
                try:
                    manual = input_fn("Enter model name (example: llama3.1:8b): ").strip()
                except EOFError:
                    output_fn("No manual model entered. Using default option.")
                    return options[default_index - 1]
                if not manual:
                    output_fn("Model name cannot be blank.")
                    continue
                return manual
            output_fn(f"Please choose a number between 1 and {len(options) + 1}.")

    def _ask_positive_int(
        self,
        question: str,
        default: int,
        minimum: int,
        input_fn: Callable[[str], str],
        output_fn: Callable[[str], None],
    ) -> int:
        while True:
            try:
                answer = input_fn(f"{question} [default {default}]: ").strip()
            except EOFError:
                output_fn(f"No input received for '{question}'. Using default.")
                return default
            if not answer:
                return default
            if not answer.isdigit():
                output_fn("Please enter a positive integer.")
                continue
            value = int(answer)
            if value < minimum:
                output_fn(f"Value must be at least {minimum}.")
                continue
            return value

    def run_setup(
        self,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> RuntimeSettings:
        current = self.load() or RuntimeSettings()
        output_fn("Runtime setup")
        output_fn("Answer the following yes/no questions.")

        enable_voice = self._ask_yes_no(
            "Enable speech-to-text and text-to-speech in GUI mode?",
            current.enable_voice_in_gui,
            input_fn,
            output_fn,
        )
        speak_replies = False
        if enable_voice:
            speak_replies = self._ask_yes_no(
                "Speak assistant replies by default?",
                current.speak_replies_by_default,
                input_fn,
                output_fn,
            )
        default_model = self._ask_choice(
            "Choose default Ollama model:",
            self.COMMON_MODEL_OPTIONS,
            input_fn,
            output_fn,
            default_index=1,
        )
        context_window_tokens = self._ask_positive_int(
            "Context window size (tokens)",
            current.context_window_tokens,
            256,
            input_fn,
            output_fn,
        )

        settings = RuntimeSettings(
            version=1,
            enable_voice_in_gui=enable_voice,
            speak_replies_by_default=speak_replies,
            default_model=default_model,
            context_window_tokens=context_window_tokens,
        )
        self.save(settings)
        output_fn(f"Saved setup to {self.settings_path}")
        return settings

    def ensure_initialized(
        self,
        interactive: bool,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> RuntimeSettings:
        current = self.load()
        if current is not None:
            return current
        if interactive:
            output_fn("First run detected. Starting setup wizard.")
            return self.run_setup(input_fn=input_fn, output_fn=output_fn)
        defaults = RuntimeSettings()
        self.save(defaults)
        output_fn(f"No interactive terminal detected. Using defaults in {self.settings_path}")
        return defaults
