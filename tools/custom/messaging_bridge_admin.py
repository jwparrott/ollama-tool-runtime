"""Messaging bridge control tool for Telegram and Twilio SMS/voice."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent_runtime.messaging_bridge import MessagingBridgeService
from agent_runtime.messaging_channels import telegram_send_message, twilio_place_tts_call, twilio_send_sms
from tools.custom.conversation_memory import run as conversation_memory_run

TOOL_SPEC = {
    "name": "messaging_bridge_admin",
    "description": (
        "Control messaging bridge behavior: check status, send Telegram/SMS messages, "
        "poll inbound messages once, and place outbound TTS calls (Twilio)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "poll_once", "send_telegram", "send_sms", "call_tts"],
                "description": "Action to perform.",
            },
            "chat_id": {"type": "string", "description": "Telegram chat id for send_telegram."},
            "to_number": {"type": "string", "description": "Destination phone number for SMS/call."},
            "text": {"type": "string", "description": "Text body for outgoing message or TTS call."},
            "voice": {"type": "string", "description": "Twilio voice for TTS call (default: alice)."},
            "language": {"type": "string", "description": "Twilio language for TTS call (default: en-US)."},
            "model": {"type": "string", "description": "Model for poll_once bridge processing."},
            "context_window_tokens": {"type": "integer", "description": "Context window for poll_once."},
            "max_steps": {"type": "integer", "description": "Max tool loop steps for poll_once."},
        },
        "required": ["action"],
    },
}


def run(args: dict, context: dict) -> dict:
    action = str(args.get("action", "")).strip().lower()
    if action not in {"status", "poll_once", "send_telegram", "send_sms", "call_tts"}:
        return {"error": "action must be one of: status, poll_once, send_telegram, send_sms, call_tts"}

    if action == "status":
        return _status(context)
    if action == "poll_once":
        return _poll_once(args, context)
    if action == "send_telegram":
        return _send_telegram(args, context)
    if action == "send_sms":
        return _send_sms(args)
    return _call_tts(args)


def _status(context: dict[str, Any]) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    state_path = project_root / ".runtime" / "messaging_bridge_state.json"
    return {
        "telegram_enabled": bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()),
        "twilio_enabled": bool(
            os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
            and os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
            and os.environ.get("TWILIO_FROM_NUMBER", "").strip()
        ),
        "state_file": str(state_path),
        "state_exists": state_path.exists(),
    }


def _poll_once(args: dict, context: dict) -> dict:
    engine = context.get("engine")
    if engine is None:
        return {"error": "poll_once requires runtime context with engine; unavailable in this call context."}
    model = str(args.get("model", "")).strip()
    if not model:
        return {"error": "model is required for poll_once."}
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    bridge = MessagingBridgeService(
        engine=engine,
        model=model,
        project_root=project_root,
        context_window_tokens=max(256, int(args.get("context_window_tokens", 8192))),
        max_steps=max(1, int(args.get("max_steps", 12))),
    )
    return bridge.run_once()


def _send_telegram(args: dict, context: dict) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"error": "TELEGRAM_BOT_TOKEN is not set."}
    chat_id = str(args.get("chat_id", "")).strip()
    text = str(args.get("text", "")).strip()
    if not chat_id or not text:
        return {"error": "chat_id and text are required for send_telegram."}
    try:
        telegram_send_message(token, chat_id=chat_id, text=text)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Telegram send failed: {exc}"}
    memory_result = conversation_memory_run(
        {
            "action": "log_turn",
            "session_id": f"telegram:{chat_id}",
            "role": "user",
            "content": text,
        },
        context,
    )
    result = {"ok": True, "channel": "telegram", "chat_id": chat_id}
    if isinstance(memory_result, dict) and "error" in memory_result:
        result["memory_logged"] = False
        result["memory_error"] = str(memory_result["error"])
    else:
        result["memory_logged"] = True
    return result


def _send_sms(args: dict) -> dict:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    to_number = str(args.get("to_number", "")).strip()
    text = str(args.get("text", "")).strip()
    if not (sid and token and from_number):
        return {"error": "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER must be set."}
    if not to_number or not text:
        return {"error": "to_number and text are required for send_sms."}
    try:
        twilio_send_sms(sid, token, from_number=from_number, to_number=to_number, body=text)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Twilio SMS failed: {exc}"}
    return {"ok": True, "channel": "sms", "to_number": to_number}


def _call_tts(args: dict) -> dict:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    to_number = str(args.get("to_number", "")).strip()
    text = str(args.get("text", "")).strip()
    voice = str(args.get("voice", "alice")).strip() or "alice"
    language = str(args.get("language", "en-US")).strip() or "en-US"
    if not (sid and token and from_number):
        return {"error": "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER must be set."}
    if not to_number or not text:
        return {"error": "to_number and text are required for call_tts."}
    try:
        response = twilio_place_tts_call(
            sid,
            token,
            from_number=from_number,
            to_number=to_number,
            message=text,
            voice=voice,
            language=language,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Twilio call failed: {exc}"}
    return {"ok": True, "channel": "voice_call", "to_number": to_number, "response": response}
