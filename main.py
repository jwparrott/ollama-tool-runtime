from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_runtime.builtin_tools import BuiltinTools
from agent_runtime.config import RuntimeConfig
from agent_runtime.engine import ToolChatEngine
from agent_runtime.messaging_bridge import MessagingBridgeService
from agent_runtime.ollama_client import OllamaClient
from agent_runtime.settings import RuntimeSettings, SettingsManager
from agent_runtime.self_update import SelfUpdater
from agent_runtime.snapshots import SnapshotManager
from agent_runtime.tool_registry import ToolRegistry
from agent_runtime.voice_webhook import TwilioVoiceWebhookService


def build_runtime(
    project_root: Path,
) -> tuple[RuntimeConfig, ToolRegistry, SnapshotManager, SelfUpdater, BuiltinTools, ToolChatEngine, SettingsManager]:
    config = RuntimeConfig(project_root=project_root)
    registry = ToolRegistry(config.registry_path)
    snapshots = SnapshotManager(project_root=project_root, snapshots_dir=config.snapshots_path)
    updater = SelfUpdater(project_root=project_root, snapshots=snapshots, default_test_command=config.default_test_command)
    builtins = BuiltinTools(project_root=project_root, registry=registry, snapshots=snapshots, updater=updater)
    engine = ToolChatEngine(
        client=OllamaClient(config.ollama_url, timeout_seconds=config.ollama_timeout_seconds),
        registry=registry,
        builtin_tools=builtins,
    )
    settings = SettingsManager(config.settings_path)
    return config, registry, snapshots, updater, builtins, engine, settings


def cli() -> None:
    parser = argparse.ArgumentParser(description="Ollama tool runtime with self-update safety.")
    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run one tool-enabled chat turn.")
    chat.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    chat.add_argument("--context-window", type=int, default=0, help="Context window tokens (defaults to configured setting)")
    chat.add_argument("--timeout", type=int, default=0, help="Ollama request timeout in seconds (default: 600)")
    chat.add_argument("--prompt", required=True, help="User prompt")

    chat_interactive = sub.add_parser("chat-interactive", help="Run an interactive multi-turn tool-enabled chat.")
    chat_interactive.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    chat_interactive.add_argument(
        "--context-window",
        type=int,
        default=0,
        help="Context window tokens (defaults to configured setting)",
    )
    chat_interactive.add_argument("--timeout", type=int, default=0, help="Ollama request timeout in seconds (default: 600)")
    chat_interactive.add_argument("--max-steps", type=int, default=12, help="Maximum tool loop steps per turn")

    gui = sub.add_parser("gui", help="Run desktop GUI chat window.")
    gui.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    gui.add_argument("--context-window", type=int, default=0, help="Context window tokens (defaults to configured setting)")
    gui.add_argument("--timeout", type=int, default=0, help="Ollama request timeout in seconds (default: 600)")
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

    bridge = sub.add_parser("bridge-run", help="Run background messaging bridge (Telegram/Twilio SMS).")
    bridge.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    bridge.add_argument("--context-window", type=int, default=0, help="Context window tokens (defaults to configured setting)")
    bridge.add_argument("--timeout", type=int, default=0, help="Ollama request timeout in seconds (default: 600)")
    bridge.add_argument("--max-steps", type=int, default=12, help="Maximum tool loop steps per incoming prompt")
    bridge.add_argument("--poll-interval", type=int, default=2, help="Polling interval between cycles in seconds")
    bridge.add_argument("--once", action="store_true", help="Run one poll cycle then exit")

    voice_bridge = sub.add_parser("voice-webhook-run", help="Run inbound Twilio voice webhook server.")
    voice_bridge.add_argument("--model", default="", help="Ollama model name (defaults to configured setting)")
    voice_bridge.add_argument("--context-window", type=int, default=0, help="Context window tokens (defaults to configured setting)")
    voice_bridge.add_argument("--timeout", type=int, default=0, help="Ollama request timeout in seconds (default: 600)")
    voice_bridge.add_argument("--max-steps", type=int, default=12, help="Maximum tool loop steps for each voice turn")
    voice_bridge.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    voice_bridge.add_argument("--port", type=int, default=8787, help="Bind port (default: 8787)")
    voice_bridge.add_argument("--path-prefix", default="/voice", help="Webhook path prefix (default: /voice)")
    voice_bridge.add_argument("--voice", default="alice", help="Twilio voice name (default: alice)")
    voice_bridge.add_argument("--language", default="en-US", help="Twilio language code (default: en-US)")
    voice_bridge.add_argument("--max-call-turns", type=int, default=12, help="Maximum turns per inbound call")

    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    config, registry, snapshots, updater, builtins, engine, settings_manager = build_runtime(root)

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
    if hasattr(args, "timeout") and args.timeout and args.timeout > 0:
        engine.client = OllamaClient(config.ollama_url, timeout_seconds=args.timeout)

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

    if args.command == "bridge-run":
        bridge = MessagingBridgeService(
            engine=engine,
            model=resolved_model,
            project_root=root,
            context_window_tokens=resolved_context_window,
            max_steps=args.max_steps,
            poll_interval_seconds=max(1, args.poll_interval),
        )
        if args.once:
            result = bridge.run_once()
            print(json.dumps(result, indent=2))
            return
        print("Messaging bridge started. Press Ctrl+C to stop.")
        try:
            bridge.run_forever()
        except KeyboardInterrupt:
            print("\nMessaging bridge stopped.")
        return

    if args.command == "voice-webhook-run":
        service = TwilioVoiceWebhookService(
            engine=engine,
            model=resolved_model,
            project_root=root,
            context_window_tokens=resolved_context_window,
            max_steps=max(1, args.max_steps),
            host=args.host,
            port=max(1, args.port),
            path_prefix=args.path_prefix,
            voice=args.voice,
            language=args.language,
            max_turns_per_call=max(1, args.max_call_turns),
        )
        print(
            "Twilio voice webhook server started. "
            f"POST {args.path_prefix.rstrip('/')}/incoming and {args.path_prefix.rstrip('/')}/gather "
            f"on {args.host}:{args.port}"
        )
        try:
            service.run()
        except KeyboardInterrupt:
            print("\nVoice webhook server stopped.")
        return

    raise SystemExit(2)


if __name__ == "__main__":
    cli()
