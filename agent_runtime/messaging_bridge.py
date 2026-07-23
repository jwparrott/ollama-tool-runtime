from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from agent_runtime.engine import ToolChatEngine
from agent_runtime.messaging_channels import (
    telegram_get_updates,
    telegram_send_message,
    twilio_list_messages,
    twilio_send_sms,
)

DEFAULT_TELEGRAM_ACK_TEXT = "Message received. Processing now..."


class MessagingBridgeService:
    def __init__(
        self,
        *,
        engine: ToolChatEngine,
        model: str,
        project_root: Path,
        context_window_tokens: int,
        max_steps: int = 12,
        poll_interval_seconds: int = 2,
    ) -> None:
        self.engine = engine
        self.model = model
        self.project_root = project_root
        self.context_window_tokens = context_window_tokens
        self.max_steps = max_steps
        self.poll_interval_seconds = poll_interval_seconds

        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_allowed_chat_ids = _parse_csv_set(os.environ.get("BRIDGE_ALLOWED_TELEGRAM_CHAT_IDS", ""))
        ack_text = str(os.environ.get("BRIDGE_TELEGRAM_ACK_TEXT", DEFAULT_TELEGRAM_ACK_TEXT)).strip()
        self.telegram_ack_text = ack_text or DEFAULT_TELEGRAM_ACK_TEXT

        self.twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from_number = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
        self.twilio_allowed_from = _parse_csv_set(os.environ.get("BRIDGE_ALLOWED_SMS_FROM", ""))

        self.state_path = self.project_root / ".runtime" / "messaging_bridge_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def run_once(self) -> dict[str, Any]:
        telegram = self._poll_telegram_once()
        sms = self._poll_twilio_sms_once()
        return {"ok": True, "telegram": telegram, "sms": sms}

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.poll_interval_seconds)

    def _poll_telegram_once(self) -> dict[str, Any]:
        if not self.telegram_bot_token:
            return {"enabled": False, "reason": "TELEGRAM_BOT_TOKEN not set"}

        offset = int(self.state.get("telegram_offset", 0))
        updates = telegram_get_updates(self.telegram_bot_token, offset=offset, timeout=20)
        processed = 0
        replies = 0
        for update in updates:
            update_id = int(update.get("update_id", 0))
            self.state["telegram_offset"] = max(int(self.state.get("telegram_offset", 0)), update_id + 1)
            message = update.get("message") or update.get("edited_message")
            if not isinstance(message, dict):
                continue

            chat = message.get("chat", {})
            chat_id = str(chat.get("id", "")).strip()
            if not chat_id:
                continue
            if self.telegram_allowed_chat_ids and chat_id not in self.telegram_allowed_chat_ids:
                continue

            prompt = str(message.get("text") or message.get("caption") or "").strip()
            if not prompt:
                continue

            processed += 1
            telegram_send_message(self.telegram_bot_token, chat_id=chat_id, text=self.telegram_ack_text)
            reply = self._run_model_for_prompt(prompt, channel="telegram", sender=chat_id)
            telegram_send_message(self.telegram_bot_token, chat_id=chat_id, text=reply)
            replies += 1

        self._save_state()
        return {"enabled": True, "processed_prompts": processed, "sent_replies": replies}

    def _poll_twilio_sms_once(self) -> dict[str, Any]:
        if not (self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number):
            return {"enabled": False, "reason": "Twilio env vars not fully set"}

        messages = twilio_list_messages(
            self.twilio_account_sid,
            self.twilio_auth_token,
            to_number=self.twilio_from_number,
            page_size=20,
        )
        processed_set = set(self.state.get("processed_sms_sids", []))
        new_sids: list[str] = []
        processed = 0
        replies = 0

        # Twilio API returns newest-first; process oldest-first for order.
        for msg in reversed(messages):
            sid = str(msg.get("sid", "")).strip()
            if not sid or sid in processed_set:
                continue
            direction = str(msg.get("direction", "")).strip().lower()
            if not direction.startswith("inbound"):
                continue
            from_number = str(msg.get("from", "")).strip()
            if self.twilio_allowed_from and from_number not in self.twilio_allowed_from:
                processed_set.add(sid)
                new_sids.append(sid)
                continue
            body = str(msg.get("body", "")).strip()
            if not body:
                processed_set.add(sid)
                new_sids.append(sid)
                continue

            processed += 1
            reply = self._run_model_for_prompt(body, channel="sms", sender=from_number)
            twilio_send_sms(
                self.twilio_account_sid,
                self.twilio_auth_token,
                from_number=self.twilio_from_number,
                to_number=from_number,
                body=reply[:1500],
            )
            replies += 1
            processed_set.add(sid)
            new_sids.append(sid)

        if new_sids:
            combined = list(processed_set)
            combined.sort()
            # cap state size
            self.state["processed_sms_sids"] = combined[-2000:]
            self._save_state()

        return {"enabled": True, "processed_prompts": processed, "sent_replies": replies}

    def _run_model_for_prompt(self, prompt: str, *, channel: str, sender: str) -> str:
        wrapper = (
            f"[Incoming {channel} message from {sender}] "
            f"Respond concisely and helpfully.\n\nUser message:\n{prompt}"
        )
        try:
            response = self.engine.run(
                model=self.model,
                user_prompt=wrapper,
                max_steps=self.max_steps,
                context_window_tokens=self.context_window_tokens,
            )
            response = str(response).strip()
            if response:
                return response
            return "I received your message but did not generate a response. Please try again."
        except Exception as exc:  # noqa: BLE001
            return f"Error while processing your request: {exc}"

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"telegram_offset": 0, "processed_sms_sids": []}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return {"telegram_offset": 0, "processed_sms_sids": []}
        if not isinstance(raw, dict):
            return {"telegram_offset": 0, "processed_sms_sids": []}
        return {
            "telegram_offset": int(raw.get("telegram_offset", 0)),
            "processed_sms_sids": [str(x) for x in raw.get("processed_sms_sids", []) if str(x).strip()],
        }

    def _save_state(self) -> None:
        payload = {
            "telegram_offset": int(self.state.get("telegram_offset", 0)),
            "processed_sms_sids": [str(x) for x in self.state.get("processed_sms_sids", [])],
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _parse_csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}
