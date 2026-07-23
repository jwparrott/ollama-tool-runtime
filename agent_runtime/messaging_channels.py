from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def telegram_get_updates(token: str, *, offset: int, timeout: int = 20) -> list[dict[str, Any]]:
    token = token.strip()
    if not token:
        raise ValueError("Telegram bot token is required.")
    query = urllib.parse.urlencode({"offset": offset, "timeout": timeout})
    url = f"https://api.telegram.org/bot{token}/getUpdates?{query}"
    payload = _http_json("GET", url)
    if not payload.get("ok"):
        description = payload.get("description", "unknown error")
        raise RuntimeError(f"Telegram getUpdates failed: {description}")
    result = payload.get("result", [])
    return result if isinstance(result, list) else []


def telegram_send_message(token: str, chat_id: str | int, text: str) -> dict[str, Any]:
    token = token.strip()
    if not token:
        raise ValueError("Telegram bot token is required.")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": str(chat_id), "text": text}
    payload = _http_json("POST", url, data)
    if not payload.get("ok"):
        description = payload.get("description", "unknown error")
        raise RuntimeError(f"Telegram sendMessage failed: {description}")
    return payload


def twilio_list_messages(account_sid: str, auth_token: str, *, to_number: str, page_size: int = 20) -> list[dict[str, Any]]:
    _validate_twilio_creds(account_sid, auth_token)
    if not to_number.strip():
        raise ValueError("Twilio to_number is required.")
    base = f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(account_sid)}/Messages.json"
    query = urllib.parse.urlencode({"To": to_number, "PageSize": str(page_size)})
    payload = _http_json("GET", f"{base}?{query}", auth_basic=_basic_auth(account_sid, auth_token))
    messages = payload.get("messages", [])
    return messages if isinstance(messages, list) else []


def twilio_send_sms(account_sid: str, auth_token: str, *, from_number: str, to_number: str, body: str) -> dict[str, Any]:
    _validate_twilio_creds(account_sid, auth_token)
    if not from_number.strip() or not to_number.strip():
        raise ValueError("Twilio from_number and to_number are required.")
    base = f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(account_sid)}/Messages.json"
    payload = _http_json(
        "POST",
        base,
        {"From": from_number, "To": to_number, "Body": body},
        auth_basic=_basic_auth(account_sid, auth_token),
    )
    return payload


def twilio_place_tts_call(
    account_sid: str,
    auth_token: str,
    *,
    from_number: str,
    to_number: str,
    message: str,
    voice: str = "alice",
    language: str = "en-US",
) -> dict[str, Any]:
    _validate_twilio_creds(account_sid, auth_token)
    if not from_number.strip() or not to_number.strip():
        raise ValueError("Twilio from_number and to_number are required.")
    escaped = (
        message.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    twiml = f'<Response><Say voice="{voice}" language="{language}">{escaped}</Say></Response>'
    base = f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(account_sid)}/Calls.json"
    payload = _http_json(
        "POST",
        base,
        {"From": from_number, "To": to_number, "Twiml": twiml},
        auth_basic=_basic_auth(account_sid, auth_token),
    )
    return payload


def _validate_twilio_creds(account_sid: str, auth_token: str) -> None:
    if not account_sid.strip() or not auth_token.strip():
        raise ValueError("Twilio account_sid and auth_token are required.")


def _basic_auth(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _http_json(
    method: str,
    url: str,
    form_data: dict[str, Any] | None = None,
    *,
    auth_basic: str | None = None,
) -> dict[str, Any]:
    data: bytes | None = None
    headers = {"User-Agent": "ollama-tool-runtime/1.0"}
    if form_data is not None:
        data = urllib.parse.urlencode({k: str(v) for k, v in form_data.items()}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if auth_basic:
        headers["Authorization"] = auth_basic

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("Request timed out.") from exc
    except OSError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc

    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response: {exc}") from exc
    return parsed if isinstance(parsed, dict) else {"data": parsed}
