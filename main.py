from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_runtime.builtin_tools import BuiltinTools
from agent_runtime.config import RuntimeConfig
from agent_runtime.engine import ToolChatEngine
from agent_runtime.ollama_client import OllamaClient
from agent_runtime.settings import RuntimeSettings, SettingsManager
from agent_runtime.self_update import SelfUpdater
from agent_runtime.snapshots import SnapshotManager
from agent_runtime.tool_registry import ToolRegistry


def build_runtime(
    project_root: Path,
) -> tuple[RuntimeConfig, ToolRegistry, SnapshotManager, SelfUpdater, BuiltinTools, ToolChatEngine, SettingsManager]:
    config = RuntimeConfig(project_root=project_root)
    registry = ToolRegistry(config.registry_path)
    snapshots = SnapshotManager(project_root=project_root, snapshots_dir=config.snapshots_path)
    updater = SelfUpdater(project_root=project_root, snapshots=snapshots, default_test_command=config.default_test_command)
    builtins = BuiltinTools(project_root=project_root, registry=registry, snapshots=snapshots, updater=updater)
    engine = ToolChatEngine(client=OllamaClient(config.ollama_url), registry=registry, builtin_tools=builtins)
    settings = SettingsManager(config.settings_path)
    return config, registry, snapshots, updater, builtins, engine, settings


def cli() -> None:
    parser = argparse.ArgumentParser(description="Ollama tool runtime with self-update safety.")
    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run one tool-enabled chat turn.")
    chat.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    chat.add_argument("--context-window", type=int, default=0, help="Context window tokens (defaults to configured setting)")
    chat.add_argument("--prompt", required=True, help="User prompt")

    chat_interactive = sub.add_parser("chat-interactive", help="Run an interactive multi-turn tool-enabled chat.")
    chat_interactive.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    chat_interactive.add_argument(
        "--context-window",
        type=int,
        default=0,
        help="Context window tokens (defaults to configured setting)",
    )
    chat_interactive.add_argument("--max-steps", type=int, default=12, help="Maximum tool loop steps per turn")

    gui = sub.add_parser("gui", help="Run desktop GUI chat window.")
    gui.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    gui.add_argument("--context-window", type=int, default=0, help="Context window tokens (defaults to configured setting)")
    gui.add_argument("--max-steps", type=int, default=12, help="Maximum tool loop steps per turn")
    gui.add_argument("--no-voice", action="store_true", help="Disable speech-to-text and text-to-speech")

    sub.add_parser("setup", help="Run interactive feature setup wizard.")

    sub.add_parser("list-tools", help="List built-in and custom tools.")

    snap = sub.add_parser("snapshot", help="Create a rollback snapshot.")
    snap.add_argument("--note", default="manual snapshot", help="Snapshot note")

    rb = sub.add_parser("rollback", help="Restore a snapshot by id.")
    rb.add_argument("--id", required=True, help="Snapshot id")

    tests = sub.add_parser("run-tests", help="Run tests command.")
    tests.add_argument("--test-cmd", default="", help="Override test command")

    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    _config, registry, snapshots, updater, builtins, engine, settings_manager = build_runtime(root)

    if args.command == "setup":
        settings = settings_manager.run_setup()
        print(json.dumps(settings.__dict__, indent=2))
        return

    settings: RuntimeSettings = settings_manager.ensure_initialized(interactive=sys.stdin.isatty())
    resolved_model = args.model if hasattr(args, "model") and args.model else settings.default_model
    resolved_context_window = (
        args.context_window
        if hasattr(args, "context_window") and args.context_window and args.context_window > 0
        else settings.context_window_tokens
    )

    if args.command == "chat":
        result = engine.run(
            model=resolved_model,
            user_prompt=args.prompt,
            context_window_tokens=resolved_context_window,
        )
        print(result)
        return

    if args.command == "chat-interactive":
        session = engine.start_session(model=resolved_model, context_window_tokens=resolved_context_window)
        print("Interactive chat started. Type 'exit' or 'quit' to stop.")
        while True:
            try:
                prompt = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not prompt:
                continue
            if prompt.lower() in {"exit", "quit"}:
                break
            result = session.ask(prompt, max_steps=args.max_steps)
            print(f"assistant> {result}")
        return

    if args.command == "gui":
        from agent_runtime.gui import run_chat_gui

        session = engine.start_session(model=resolved_model, context_window_tokens=resolved_context_window)
        run_chat_gui(
            session=session,
            model=resolved_model,
            max_steps=args.max_steps,
            enable_voice=(settings.enable_voice_in_gui and not args.no_voice),
            speak_replies_default=settings.speak_replies_by_default,
        )
        return

    if args.command == "list-tools":
        print(json.dumps(builtins.list_tools({}), indent=2))
        return

    if args.command == "snapshot":
        record = snapshots.create(note=args.note)
        print(json.dumps(record.__dict__, indent=2))
        return

    if args.command == "rollback":
        snapshots.restore(args.id)
        print(json.dumps({"ok": True, "restored_snapshot_id": args.id}, indent=2))
        return

    if args.command == "run-tests":
        command = args.test_cmd if args.test_cmd else None
        result = updater.run_tests(command=command)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ok"] else 1)

    raise SystemExit(2)


if __name__ == "__main__":
    cli()
