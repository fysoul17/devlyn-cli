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


def collect_stdout(stdout_path: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    stdout_text = stdout_path.read_text(encoding="utf-8")
    try:
        candidate = loads_strict_json(stdout_text)
    except ValueError:
        candidate = None
    if not isinstance(candidate, dict) or not ENVELOPE_KEYS.issubset(candidate) or "severity" in candidate:
        return collect_text(stdout_text, stdout_path)
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
