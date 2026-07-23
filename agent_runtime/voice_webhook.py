from __future__ import annotations

import json
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from xml.sax.saxutils import escape as xml_escape

from agent_runtime.engine import ToolChatEngine


@dataclass
class VoiceSession:
    call_sid: str
    from_number: str
    to_number: str
    turns: list[dict[str, str]]
    created_at: float
    updated_at: float


class TwilioVoiceWebhookService:
    def __init__(
        self,
        *,
        engine: ToolChatEngine,
        model: str,
        project_root: Path,
        context_window_tokens: int,
        max_steps: int = 12,
        host: str = "0.0.0.0",
        port: int = 8787,
        path_prefix: str = "/voice",
        voice: str = "alice",
        language: str = "en-US",
        max_turns_per_call: int = 12,
    ) -> None:
        self.engine = engine
        self.model = model
        self.project_root = project_root
        self.context_window_tokens = context_window_tokens
        self.max_steps = max_steps
        self.host = host
        self.port = port
        self.path_prefix = "/" + path_prefix.strip("/").replace("\\", "/")
        self.voice = voice
        self.language = language
        self.max_turns_per_call = max_turns_per_call

        self.state_path = self.project_root / ".runtime" / "voice_webhook_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, VoiceSession] = {}
        self._load_state()

    def run(self) -> None:
        service = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                service._handle_http(self, method="GET")

            def do_POST(self):
                service._handle_http(self, method="POST")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                _ = format
                _ = args
                return

        server = HTTPServer((self.host, self.port), _Handler)
        try:
            server.serve_forever()
        finally:
            self._save_state()
            server.server_close()

    def _handle_http(self, handler: BaseHTTPRequestHandler, *, method: str) -> None:
        if method == "GET":
            self._respond_json(
                handler,
                200,
                {
                    "ok": True,
                    "service": "twilio-voice-webhook",
                    "path_prefix": self.path_prefix,
                    "sessions": len(self._sessions),
                },
            )
            return

        path = handler.path.split("?", 1)[0]
        length = int(handler.headers.get("Content-Length", "0") or "0")
        body = handler.rfile.read(length).decode("utf-8", errors="replace")
        form = _parse_form_encoded(body)

        if path == f"{self.path_prefix}/incoming":
            twiml = self._handle_incoming(form)
            self._respond_twiml(handler, twiml)
            return
        if path == f"{self.path_prefix}/gather":
            twiml = self._handle_gather(form)
            self._respond_twiml(handler, twiml)
            return
        self._respond_twiml(handler, _twiml_say_hangup("Unknown voice webhook endpoint."))

    def _handle_incoming(self, form: dict[str, str]) -> str:
        call_sid = form.get("CallSid", "").strip()
        from_number = form.get("From", "").strip()
        to_number = form.get("To", "").strip()
        if call_sid:
            now = time.time()
            self._sessions.setdefault(
                call_sid,
                VoiceSession(
                    call_sid=call_sid,
                    from_number=from_number,
                    to_number=to_number,
                    turns=[],
                    created_at=now,
                    updated_at=now,
                ),
            )
            self._save_state()
        prompt = "Hello. I am your AI assistant. Please tell me how I can help."
        return _twiml_gather(
            say_text=prompt,
            action=f"{self.path_prefix}/gather",
            voice=self.voice,
            language=self.language,
            finish_on_timeout=True,
        )

    def _handle_gather(self, form: dict[str, str]) -> str:
        call_sid = form.get("CallSid", "").strip()
        speech = form.get("SpeechResult", "").strip()
        digits = form.get("Digits", "").strip()
        utterance = speech if speech else digits

        if not call_sid:
            return _twiml_say_hangup("Missing CallSid in request.")

        session = self._sessions.get(call_sid)
        if session is None:
            now = time.time()
            session = VoiceSession(
                call_sid=call_sid,
                from_number=form.get("From", "").strip(),
                to_number=form.get("To", "").strip(),
                turns=[],
                created_at=now,
                updated_at=now,
            )
            self._sessions[call_sid] = session

        if not utterance:
            return _twiml_gather(
                say_text="I didn't catch that. Please say that again.",
                action=f"{self.path_prefix}/gather",
                voice=self.voice,
                language=self.language,
                finish_on_timeout=True,
            )

        session.turns.append({"role": "user", "text": utterance})
        if len([t for t in session.turns if t.get("role") == "user"]) > self.max_turns_per_call:
            self._save_state()
            return _twiml_say_hangup("We've reached the turn limit for this call. Goodbye.")

        prompt = self._build_prompt(session)
        try:
            reply = self.engine.run(
                model=self.model,
                user_prompt=prompt,
                max_steps=self.max_steps,
                context_window_tokens=self.context_window_tokens,
            )
            reply_text = str(reply).strip() or "I don't have a response right now."
        except Exception as exc:  # noqa: BLE001
            reply_text = f"I hit an error while processing your request: {exc}"

        session.turns.append({"role": "assistant", "text": reply_text})
        session.updated_at = time.time()
        self._save_state()

        return _twiml_gather(
            say_text=reply_text + " You can continue speaking after the tone.",
            action=f"{self.path_prefix}/gather",
            voice=self.voice,
            language=self.language,
            finish_on_timeout=True,
        )

    def _build_prompt(self, session: VoiceSession) -> str:
        history = session.turns[-10:]
        rendered = []
        for turn in history:
            role = turn.get("role", "user")
            text = turn.get("text", "")
            rendered.append(f"{role}: {text}")
        transcript = "\n".join(rendered)
        return (
            "You are assisting in a live phone conversation. "
            "Respond clearly and concisely for spoken audio. "
            "Avoid markdown and avoid long lists.\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            "Provide your next spoken reply."
        )

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return
        sessions = raw.get("sessions", {})
        if not isinstance(sessions, dict):
            return
        loaded: dict[str, VoiceSession] = {}
        for sid, payload in sessions.items():
            if not isinstance(payload, dict):
                continue
            turns = payload.get("turns", [])
            if not isinstance(turns, list):
                turns = []
            clean_turns: list[dict[str, str]] = []
            for item in turns:
                if isinstance(item, dict):
                    role = str(item.get("role", "user"))
                    text = str(item.get("text", ""))
                    clean_turns.append({"role": role, "text": text})
            loaded[sid] = VoiceSession(
                call_sid=sid,
                from_number=str(payload.get("from_number", "")),
                to_number=str(payload.get("to_number", "")),
                turns=clean_turns[-50:],
                created_at=float(payload.get("created_at", time.time())),
                updated_at=float(payload.get("updated_at", time.time())),
            )
        self._sessions = loaded

    def _save_state(self) -> None:
        payload = {
            "sessions": {
                sid: {
                    "from_number": session.from_number,
                    "to_number": session.to_number,
                    "turns": session.turns[-50:],
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
                for sid, session in self._sessions.items()
            }
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _respond_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    @staticmethod
    def _respond_twiml(handler: BaseHTTPRequestHandler, twiml: str) -> None:
        data = twiml.encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "text/xml; charset=utf-8")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)


def _parse_form_encoded(body: str) -> dict[str, str]:
    parsed = parse_qs(body, keep_blank_values=True)
    result: dict[str, str] = {}
    for key, values in parsed.items():
        result[str(key)] = str(values[0]) if values else ""
    return result


def _twiml_gather(
    *,
    say_text: str,
    action: str,
    voice: str,
    language: str,
    finish_on_timeout: bool,
) -> str:
    escaped = xml_escape(say_text)
    escaped_action = xml_escape(action)
    timeout = "auto" if finish_on_timeout else "3"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech dtmf" action="{escaped_action}" method="POST" speechTimeout="{timeout}" timeout="5">'
        f'<Say voice="{xml_escape(voice)}" language="{xml_escape(language)}">{escaped}</Say>'
        "</Gather>"
        f'<Say voice="{xml_escape(voice)}" language="{xml_escape(language)}">I did not receive input. Goodbye.</Say>'
        "<Hangup/>"
        "</Response>"
    )


def _twiml_say_hangup(text: str) -> str:
    escaped = xml_escape(text)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say>{escaped}</Say>"
        "<Hangup/>"
        "</Response>"
    )
