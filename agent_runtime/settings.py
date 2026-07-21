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


class SettingsManager:
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

        settings = RuntimeSettings(
            version=1,
            enable_voice_in_gui=enable_voice,
            speak_replies_by_default=speak_replies,
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
