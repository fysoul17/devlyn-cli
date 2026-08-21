#!/usr/bin/env python3
"""Parse the one permitted pair-JUDGE stdout emission contract."""

from __future__ import annotations

import json
import pathlib
from typing import Any


FINDING_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
VERDICTS = {"PASS", "PASS_WITH_ISSUES", "FAIL", "NEEDS_WORK", "BLOCKED"}
ENVELOPE_KEYS = {"text", "stopReason", "sessionId", "requestId"}
IGNORABLE_FENCES = {"```", "```json", "```jsonl"}
NARRATIVE_PREAMBLE_BYTES = frozenset(
    b"\t\n\r !\"$%&'()*+,-./0123456789:;<=>?@"
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_abcdefghijklmnopqrstuvwxyz|}~"
) | frozenset(range(0x80, 0x100))
STREAM_RECORD_TYPES = {"system", "assistant", "user", "result"}


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str) -> Any:
    return json.loads(text, parse_constant=reject_json_constant)


def collect_text(text: str, source: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    findings: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        raw = line.strip()
        if not raw or raw in IGNORABLE_FENCES:
            continue
        if raw.startswith("# SUMMARY "):
            if summary is not None:
                raise SystemExit(f"error: record after terminal verdict at {source}:{line_no}")
            try:
                item = loads_strict_json(raw.removeprefix("# SUMMARY ").strip())
            except ValueError as exc:
                raise SystemExit(f"error: invalid SUMMARY JSON at {source}:{line_no}: {exc}")
            if not isinstance(item, dict) or item.get("verdict") not in VERDICTS:
                raise SystemExit(f"error: verdict has unknown value at {source}:{line_no}")
            summary = item
            continue
        if summary is not None:
            raise SystemExit(f"error: record after terminal verdict at {source}:{line_no}")
        if raw in VERDICTS:
            summary = {"verdict": raw}
            continue
        try:
            item = loads_strict_json(raw)
        except ValueError as exc:
            raise SystemExit(f"error: invalid JSONL at {source}:{line_no}: {exc}")
        if not isinstance(item, dict):
            raise SystemExit(f"error: JSONL item is not an object at {source}:{line_no}")
        severity = str(item.get("severity") or "").upper()
        if severity not in FINDING_SEVERITIES:
            raise SystemExit(f"error: finding missing valid severity at {source}:{line_no}")
        findings.append(item)
    return findings, summary


def recover_envelope_text(text: str, source: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    encoded = text.encode("utf-8")
    for cut, byte in enumerate(encoded[:-1], 1):
        if byte not in NARRATIVE_PREAMBLE_BYTES:
            break
        try:
            findings, summary = collect_text(encoded[cut:].decode("utf-8"), source)
        except (UnicodeDecodeError, SystemExit):
            continue
        if summary is not None and summary.get("verdict") == "NEEDS_WORK" and findings:
            return findings, summary
    raise SystemExit("error: no admissible envelope recovery")


def collect_message_stream(
    text: str, source: pathlib.Path
) -> tuple[list[dict[str, Any]], dict[str, Any] | None] | None:
    """Bind adjudication to a whole-message NDJSON stream's terminal assistant turn.

    Returns None when the first record does not declare that stream. Once it does,
    this returns or rejects: tool and narration turns are never forwarded, and no
    envelope recovery is attempted.
    """
    lines = [(no, raw) for no, line in enumerate(text.splitlines(), 1) if (raw := line.strip())]
    if not lines:
        return None
    try:
        first = loads_strict_json(lines[0][1])
    except ValueError:
        return None
    if (
        not isinstance(first, dict)
        or first.get("type") != "system"
        or str(first.get("severity") or "").upper() in FINDING_SEVERITIES
    ):
        return None
    if first.get("subtype") != "init":
        raise SystemExit(f"error: stream must open with system/init at {source}:{lines[0][0]}")
    records = [first]
    for line_no, raw in lines[1:]:
        try:
            item = loads_strict_json(raw)
        except ValueError as exc:
            raise SystemExit(f"error: invalid stream NDJSON at {source}:{line_no}: {exc}")
        if not isinstance(item, dict) or item.get("type") not in STREAM_RECORD_TYPES:
            raise SystemExit(f"error: unknown stream record at {source}:{line_no}")
        if item["type"] == "system":
            raise SystemExit(f"error: stream has a second system record at {source}:{line_no}")
        records.append(item)

    results = [item for item in records if item["type"] == "result"]
    if len(results) != 1 or results[0] is not records[-1]:
        raise SystemExit(f"error: stream needs exactly one terminal result at {source}")
    result = results[0]
    if (
        result.get("subtype") != "success"
        or result.get("is_error") is not False
        or result.get("stop_reason") != "end_turn"
    ):
        raise SystemExit(f"error: stream result is not a successful end_turn at {source}")

    assistants = [item for item in records if item["type"] == "assistant"]
    terminals = [
        item
        for item in assistants
        if isinstance(item.get("message"), dict) and item["message"].get("stop_reason") == "end_turn"
    ]
    if (
        len(terminals) != 1
        or terminals[0] is not assistants[-1]
        or terminals[0] is not records[-2]
    ):
        raise SystemExit(f"error: stream needs exactly one final end_turn assistant message at {source}")

    session = first.get("session_id")
    if not isinstance(session, str) or any(
        item.get("session_id") != session for item in (terminals[0], result)
    ):
        raise SystemExit(f"error: stream session identity does not agree at {source}")

    blocks = terminals[0]["message"].get("content")
    if not isinstance(blocks, list):
        raise SystemExit(f"error: stream terminal message has no content blocks at {source}")
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            raise SystemExit(f"error: stream content block is not an object at {source}")
        if block.get("type") == "text":
            if not isinstance(block.get("text"), str):
                raise SystemExit(f"error: stream text block is not a string at {source}")
            parts.append(block["text"])
    message_text = "".join(parts)
    if result.get("result") != message_text:
        raise SystemExit(f"error: stream result text does not match the terminal message at {source}")
    return collect_text(message_text, source)


def collect_stdout(stdout_path: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    stdout_text = stdout_path.read_text(encoding="utf-8")
    try:
        candidate = loads_strict_json(stdout_text)
    except ValueError:
        candidate = None
    if isinstance(candidate, dict) and ENVELOPE_KEYS.issubset(candidate) and "severity" not in candidate:
        if candidate["stopReason"] != "EndTurn":
            raise SystemExit(
                f"error: envelope stopReason must be 'EndTurn' at {stdout_path}; "
                f"got {candidate['stopReason']!r}"
            )
        if not isinstance(candidate["text"], str):
            raise SystemExit(f"error: envelope text must be a string at {stdout_path}")
        try:
            return collect_text(candidate["text"], stdout_path)
        except SystemExit as exc:
            try:
                return recover_envelope_text(candidate["text"], stdout_path)
            except SystemExit:
                raise SystemExit(f"error: envelope text rejected: {exc}") from None
    stream = collect_message_stream(stdout_text, stdout_path)
    if stream is not None:
        return stream
    return collect_text(stdout_text, stdout_path)
