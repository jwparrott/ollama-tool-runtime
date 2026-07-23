"""Collect, clean, and parse unstructured transcript-style data from shared sources."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib import request

TOOL_SPEC = {
    "name": "shared_data_cleaner_parser",
    "description": (
        "Collect and clean unstructured data from text, local files, and URLs, then parse "
        "conversation turns for single-speaker or multi-speaker transcripts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "raw_text": {"type": "string", "description": "Raw text to parse directly."},
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of local file paths or URLs to ingest.",
            },
            "speaker_mode": {
                "type": "string",
                "enum": ["auto", "single", "multi"],
                "description": "How to interpret speaker labels. Default: auto.",
            },
            "merge_consecutive_turns": {
                "type": "boolean",
                "description": "If true, merge adjacent turns by the same speaker. Default true.",
            },
            "include_dialogue_pairs": {
                "type": "boolean",
                "description": "If true, include adjacent back-and-forth speaker pairs.",
            },
            "max_chars_per_source": {
                "type": "integer",
                "description": "Maximum chars to read per source (1000-200000, default 50000).",
            },
        },
    },
}

_SPEAKER_PATTERNS = (
    re.compile(
        r"^\s*(?:\[(?P<ts1>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*)?"
        r"(?P<speaker>[A-Za-z][A-Za-z0-9 _.'-]{0,40})\s*(?::|-|\|)\s*(?P<text>.+)$"
    ),
    re.compile(
        r"^\s*(?P<speaker>[A-Za-z][A-Za-z0-9 _.'-]{0,40})\s*\((?P<role>[^)]+)\)\s*:\s*(?P<text>.+)$"
    ),
)

_LEADING_TIMESTAMP = re.compile(
    r"^\s*(?:\[?\(?\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\)?\]?"
    r"|\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?)\s*[-|]?\s*"
)


def run(args: dict, context: dict) -> dict:
    raw_text = str(args.get("raw_text", ""))
    sources = args.get("sources") or []
    speaker_mode = str(args.get("speaker_mode", "auto")).strip().lower() or "auto"
    merge_turns = bool(args.get("merge_consecutive_turns", True))
    include_pairs = bool(args.get("include_dialogue_pairs", True))
    max_chars = min(max(1000, int(args.get("max_chars_per_source", 50000))), 200000)

    if speaker_mode not in {"auto", "single", "multi"}:
        return {"error": "speaker_mode must be one of: auto, single, multi"}
    if raw_text.strip() == "" and not sources:
        return {"error": "Provide raw_text and/or sources."}
    if not isinstance(sources, list):
        return {"error": "sources must be an array of file paths or URLs."}

    blobs = []
    source_reports = []
    if raw_text.strip():
        cleaned = _clean_text(raw_text)
        blobs.append(("raw_text", cleaned))
        source_reports.append({"source": "raw_text", "chars": len(cleaned), "ok": True})

    for item in sources:
        source = str(item).strip()
        if not source:
            continue
        text, report = _read_source(source, context, max_chars)
        source_reports.append(report)
        if text is not None:
            blobs.append((source, _clean_text(text)))

    if not blobs:
        return {"error": "No readable content found in provided sources.", "sources": source_reports}

    turns: list[dict[str, Any]] = []
    for source_name, blob in blobs:
        turns.extend(_parse_turns(blob, source_name, speaker_mode))

    if merge_turns:
        turns = _merge_consecutive(turns)
    for idx, turn in enumerate(turns, start=1):
        turn["turn_index"] = idx

    speakers = sorted({str(turn.get("speaker", "Unknown")) for turn in turns})
    speaker_counts: dict[str, int] = {}
    for turn in turns:
        speaker = str(turn.get("speaker", "Unknown"))
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

    response = {
        "source_count": len(blobs),
        "sources": source_reports,
        "turn_count": len(turns),
        "speaker_count": len(speakers),
        "speakers": speakers,
        "speaker_turn_counts": speaker_counts,
        "turns": turns,
    }
    if include_pairs:
        response["dialogue_pairs"] = _dialogue_pairs(turns)
    return response


def _read_source(source: str, context: dict, max_chars: int) -> tuple[str | None, dict[str, Any]]:
    if source.lower().startswith(("http://", "https://")):
        req = request.Request(source, headers={"User-Agent": "ollama-tool-runtime/1.0"})
        try:
            with request.urlopen(req, timeout=20) as resp:
                body = resp.read(max_chars).decode("utf-8", errors="replace")
            return body, {"source": source, "chars": len(body), "ok": True}
        except TimeoutError:
            return None, {"source": source, "ok": False, "error": "request timed out"}
        except OSError as exc:
            return None, {"source": source, "ok": False, "error": str(exc)}

    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    path = Path(source)
    if not path.is_absolute():
        path = (project_root / source).resolve()
    try:
        path.relative_to(project_root)
    except ValueError:
        return None, {"source": source, "ok": False, "error": "path outside project root"}
    if not path.exists() or path.is_dir():
        return None, {"source": source, "ok": False, "error": "path not found or not a file"}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, {"source": source, "ok": False, "error": str(exc)}
    if len(text) > max_chars:
        text = text[:max_chars]
    return text, {"source": source, "chars": len(text), "ok": True}


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_turns(blob: str, source_name: str, speaker_mode: str) -> list[dict[str, Any]]:
    lines = blob.split("\n")
    turns: list[dict[str, Any]] = []
    single_speaker_name = "Speaker_1"
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        line = _LEADING_TIMESTAMP.sub("", line).strip()
        if not line:
            continue

        parsed = _extract_speaker_line(line)
        if speaker_mode == "single":
            speaker = single_speaker_name
            text = line
        elif parsed is not None:
            speaker = parsed["speaker"]
            text = parsed["text"]
        elif speaker_mode == "multi":
            speaker = "Unknown"
            text = line
        else:  # auto
            if parsed is not None:
                speaker = parsed["speaker"]
                text = parsed["text"]
            else:
                speaker = "Speaker_1"
                text = line

        turns.append(
            {
                "source": source_name,
                "line_number": idx,
                "speaker": speaker,
                "text": text.strip(),
            }
        )
    return turns


def _extract_speaker_line(line: str) -> dict[str, str] | None:
    for pattern in _SPEAKER_PATTERNS:
        match = pattern.match(line)
        if not match:
            continue
        speaker = match.group("speaker").strip()
        text = match.group("text").strip()
        if not speaker or not text:
            continue
        if len(speaker.split()) > 6:
            continue
        return {"speaker": speaker, "text": text}
    return None


def _merge_consecutive(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not turns:
        return []
    merged = [dict(turns[0])]
    for turn in turns[1:]:
        last = merged[-1]
        if turn.get("speaker") == last.get("speaker") and turn.get("source") == last.get("source"):
            last["text"] = f"{last.get('text', '')} {turn.get('text', '')}".strip()
            continue
        merged.append(dict(turn))
    return merged


def _dialogue_pairs(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = []
    for i in range(len(turns) - 1):
        first = turns[i]
        second = turns[i + 1]
        if first.get("speaker") == second.get("speaker"):
            continue
        pairs.append(
            {
                "from_speaker": first.get("speaker"),
                "to_speaker": second.get("speaker"),
                "from_text": first.get("text"),
                "to_text": second.get("text"),
            }
        )
    return pairs
