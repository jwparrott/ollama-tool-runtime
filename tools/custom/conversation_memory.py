"""Persistent conversation memory with user reinforcement feedback."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOL_SPEC = {
    "name": "conversation_memory",
    "description": (
        "Store and query conversation history, outcomes, and user feedback. "
        "Supports positive/negative reinforcement to improve future decisions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["log_turn", "add_feedback", "query_history", "decision_context", "list_sessions"],
                "description": "Operation to perform.",
            },
            "session_id": {"type": "string", "description": "Conversation/session identifier."},
            "role": {"type": "string", "description": "Role for log_turn (user/assistant/system/tool)."},
            "content": {"type": "string", "description": "Message content for log_turn."},
            "intent": {"type": "string", "description": "Intent label for log_turn."},
            "decision": {"type": "string", "description": "Decision made by assistant/tool, if any."},
            "outcome": {"type": "string", "description": "Observed outcome after decision."},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags."},
            "entry_id": {"type": "string", "description": "Entry id for add_feedback."},
            "feedback": {
                "type": "string",
                "enum": ["positive", "neutral", "negative"],
                "description": "User reinforcement signal for add_feedback.",
            },
            "feedback_comment": {"type": "string", "description": "Optional free-text feedback note."},
            "query": {"type": "string", "description": "Search text for query_history/decision_context."},
            "limit": {"type": "integer", "description": "Maximum results to return (1-100, default 10)."},
        },
        "required": ["action"],
    },
}


def run(args: dict, context: dict) -> dict:
    action = str(args.get("action", "")).strip().lower()
    if not action:
        return {"error": "action is required"}

    memory_path = _memory_path(context)
    if action == "log_turn":
        return _log_turn(args, memory_path)
    if action == "add_feedback":
        return _add_feedback(args, memory_path)
    if action == "query_history":
        return _query_history(args, memory_path)
    if action == "decision_context":
        return _decision_context(args, memory_path)
    if action == "list_sessions":
        return _list_sessions(memory_path)
    return {"error": f"Unknown action '{action}'."}


def _memory_path(context: dict[str, Any]) -> Path:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    path = project_root / ".runtime" / "conversation_memory.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                entries.append(item)
    return entries


def _write_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    payload = "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries)
    if payload:
        payload += "\n"
    path.write_text(payload, encoding="utf-8")


def _append_entry(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False))
        handle.write("\n")


def _log_turn(args: dict, path: Path) -> dict:
    session_id = str(args.get("session_id", "default")).strip() or "default"
    role = str(args.get("role", "assistant")).strip().lower() or "assistant"
    content = str(args.get("content", "")).strip()
    if not content:
        return {"error": "content is required for log_turn"}
    intent = str(args.get("intent", "")).strip()
    decision = str(args.get("decision", "")).strip()
    outcome = str(args.get("outcome", "")).strip()
    raw_tags = args.get("tags") or []
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]

    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": _now_iso(),
        "session_id": session_id,
        "role": role,
        "content": content,
        "intent": intent,
        "decision": decision,
        "outcome": outcome,
        "tags": tags,
        "feedback": "neutral",
        "feedback_comment": "",
    }
    _append_entry(path, entry)
    return {"ok": True, "entry_id": entry["id"], "session_id": session_id}


def _add_feedback(args: dict, path: Path) -> dict:
    entry_id = str(args.get("entry_id", "")).strip()
    feedback = str(args.get("feedback", "")).strip().lower()
    feedback_comment = str(args.get("feedback_comment", "")).strip()
    if not entry_id:
        return {"error": "entry_id is required for add_feedback"}
    if feedback not in {"positive", "neutral", "negative"}:
        return {"error": "feedback must be one of: positive, neutral, negative"}

    entries = _read_entries(path)
    for entry in entries:
        if str(entry.get("id")) == entry_id:
            entry["feedback"] = feedback
            entry["feedback_comment"] = feedback_comment
            entry["feedback_timestamp"] = _now_iso()
            _write_entries(path, entries)
            return {"ok": True, "entry_id": entry_id, "feedback": feedback}
    return {"error": f"entry_id not found: {entry_id}"}


def _query_history(args: dict, path: Path) -> dict:
    query = str(args.get("query", "")).strip().lower()
    session_id = str(args.get("session_id", "")).strip()
    limit = min(max(1, int(args.get("limit", 10))), 100)
    entries = _read_entries(path)

    ranked: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        if session_id and str(entry.get("session_id")) != session_id:
            continue
        score = _match_score(entry, query)
        if query and score <= 0:
            continue
        ranked.append((score, entry))
    ranked.sort(key=lambda item: (item[0], item[1].get("timestamp", "")), reverse=True)

    items = [
        {
            "id": entry.get("id"),
            "timestamp": entry.get("timestamp"),
            "session_id": entry.get("session_id"),
            "role": entry.get("role"),
            "content": entry.get("content"),
            "decision": entry.get("decision"),
            "outcome": entry.get("outcome"),
            "feedback": entry.get("feedback", "neutral"),
            "tags": entry.get("tags", []),
        }
        for _, entry in ranked[:limit]
    ]
    return {"query": query, "result_count": len(items), "entries": items}


def _decision_context(args: dict, path: Path) -> dict:
    query = str(args.get("query", "")).strip().lower()
    if not query:
        return {"error": "query is required for decision_context"}
    limit = min(max(1, int(args.get("limit", 20))), 100)
    matches = _query_history({"query": query, "limit": limit}, path).get("entries", [])

    positive = [entry for entry in matches if entry.get("feedback") == "positive"]
    negative = [entry for entry in matches if entry.get("feedback") == "negative"]

    recommended = _extract_highlights(positive, key="decision")
    cautions = _extract_highlights(negative, key="decision")
    failure_modes = _extract_highlights(negative, key="outcome")

    return {
        "query": query,
        "match_count": len(matches),
        "positive_count": len(positive),
        "negative_count": len(negative),
        "recommended_actions": recommended[:5],
        "cautions": cautions[:5],
        "failure_modes": failure_modes[:5],
        "supporting_entries": matches[:10],
    }


def _list_sessions(path: Path) -> dict:
    entries = _read_entries(path)
    counts: dict[str, int] = {}
    for entry in entries:
        session_id = str(entry.get("session_id", "default"))
        counts[session_id] = counts.get(session_id, 0) + 1
    sessions = [{"session_id": sid, "entry_count": count} for sid, count in sorted(counts.items())]
    return {"session_count": len(sessions), "sessions": sessions}


def _match_score(entry: dict[str, Any], query: str) -> int:
    if not query:
        return 1
    haystack = " ".join(
        str(entry.get(key, ""))
        for key in ("content", "intent", "decision", "outcome", "feedback_comment", "session_id")
    ).lower()
    tokens = [token for token in query.split() if token]
    if not tokens:
        return 0
    return sum(2 if token in haystack else 0 for token in tokens) + (3 if query in haystack else 0)


def _extract_highlights(entries: list[dict[str, Any]], key: str) -> list[str]:
    seen: set[str] = set()
    highlights: list[str] = []
    for entry in entries:
        value = str(entry.get(key, "")).strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        highlights.append(value)
    return highlights
