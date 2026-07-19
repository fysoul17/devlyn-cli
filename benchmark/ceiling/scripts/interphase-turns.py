#!/usr/bin/env python3
"""Count API-request turns and wall time outside recorded phase spans."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


ISO_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})"
)
API_REQUEST_RE = re.compile(
    r"\b(api[- ]request|api request|request start|sending request)\b|"
    r"/v1/(messages|responses|chat/completions)",
    re.IGNORECASE,
)


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


def parse_time(value: object) -> dt.datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value > 10_000_000_000:
            value = value / 1000
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    elif re.search(r"[+-]\d{4}$", text):
        text = text[:-5] + text[-5:-2] + ":" + text[-2:]
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def extract_line_time(line: str) -> dt.datetime | None:
    stripped = line.strip()
    if stripped.startswith("{"):
        try:
            data = loads_strict_json(stripped)
        except ValueError:
            data = None
        if isinstance(data, dict):
            for key in ("timestamp", "time", "created_at", "createdAt", "ts"):
                parsed = parse_time(data.get(key))
                if parsed is not None:
                    return parsed
    match = ISO_RE.search(line)
    if not match:
        return None
    return parse_time(match.group(0))


def iso(value: dt.datetime) -> str:
    value = value.astimezone(dt.timezone.utc)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def phase_spans(state: dict) -> list[tuple[dt.datetime, dt.datetime]]:
    spans: list[tuple[dt.datetime, dt.datetime]] = []
    phases = state.get("phases")
    if not isinstance(phases, dict):
        return spans
    for entry in phases.values():
        if not isinstance(entry, dict):
            continue
        add_span_from_record(entry, spans)
        history = entry.get("history")
        if isinstance(history, list):
            for item in history:
                if isinstance(item, dict):
                    add_span_from_record(item, spans)
    return spans


def add_span_from_record(record: dict, spans: list[tuple[dt.datetime, dt.datetime]]) -> None:
    start = parse_time(record.get("started_at"))
    end = parse_time(record.get("completed_at"))
    if start is None or end is None or end <= start:
        return
    spans.append((start, end))


def clipped_union(
    spans: list[tuple[dt.datetime, dt.datetime]],
    start: dt.datetime,
    end: dt.datetime,
) -> list[tuple[dt.datetime, dt.datetime]]:
    clipped = [
        (max(span_start, start), min(span_end, end))
        for span_start, span_end in spans
        if span_end > start and span_start < end
    ]
    clipped = [(span_start, span_end) for span_start, span_end in clipped if span_end > span_start]
    clipped.sort(key=lambda item: item[0])
    merged: list[tuple[dt.datetime, dt.datetime]] = []
    for span_start, span_end in clipped:
        if not merged or span_start > merged[-1][1]:
            merged.append((span_start, span_end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], span_end))
    return merged


def gaps_between(
    covered: list[tuple[dt.datetime, dt.datetime]],
    start: dt.datetime,
    end: dt.datetime,
) -> list[tuple[dt.datetime, dt.datetime]]:
    gaps: list[tuple[dt.datetime, dt.datetime]] = []
    cursor = start
    for span_start, span_end in covered:
        if span_start > cursor:
            gaps.append((cursor, span_start))
        cursor = max(cursor, span_end)
    if cursor < end:
        gaps.append((cursor, end))
    return gaps


def in_windows(value: dt.datetime, windows: list[tuple[dt.datetime, dt.datetime]]) -> bool:
    return any(start <= value < end for start, end in windows)


def count_api_requests(debug_log: Path, windows: list[tuple[dt.datetime, dt.datetime]]) -> int:
    count = 0
    with debug_log.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not API_REQUEST_RE.search(line):
                continue
            timestamp = extract_line_time(line)
            if timestamp is not None and in_windows(timestamp, windows):
                count += 1
    return count


def self_test() -> int:
    state = {
        "phases": {
            "implement": {
                "started_at": "2026-07-19T00:00:03Z",
                "completed_at": "2026-07-19T00:00:04Z",
                "history": [
                    {
                        "started_at": "2026-07-19T00:00:01Z",
                        "completed_at": "2026-07-19T00:00:02Z",
                    }
                ],
            }
        }
    }
    spans = phase_spans(state)
    history_span = (
        parse_time("2026-07-19T00:00:01Z"),
        parse_time("2026-07-19T00:00:02Z"),
    )
    if len(spans) != 2 or history_span not in spans:
        raise AssertionError(f"history[] re-entry span was not consumed: {spans!r}")
    print("SELFTEST PASS: interphase history[] re-entry span consumed")
    return 0


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug-log", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()

    debug_log = Path(args.debug_log)
    state_path = Path(args.state)
    if not debug_log.is_file():
        parser.error(f"--debug-log not found: {debug_log}")
    if not state_path.is_file():
        parser.error(f"--state not found: {state_path}")
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"error: cannot read state: {exc}", file=sys.stderr)
        return 2
    if not isinstance(state, dict):
        print("error: state must be a JSON object", file=sys.stderr)
        return 2

    run_start = parse_time(state.get("started_at"))
    verify_phase = state.get("phases", {}).get("verify") if isinstance(state.get("phases"), dict) else None
    verify_start = parse_time(verify_phase.get("started_at")) if isinstance(verify_phase, dict) else None
    if run_start is None:
        print("error: state.started_at is missing or malformed", file=sys.stderr)
        return 2
    if verify_start is None:
        print("error: phases.verify.started_at is missing or malformed", file=sys.stderr)
        return 2
    if verify_start <= run_start:
        print("error: phases.verify.started_at must be after state.started_at", file=sys.stderr)
        return 2

    covered = clipped_union(phase_spans(state), run_start, verify_start)
    windows = gaps_between(covered, run_start, verify_start)
    api_turns = count_api_requests(debug_log, windows)
    wall_seconds = sum((end - start).total_seconds() for start, end in windows)

    print(json.dumps({
        "debug_log": str(debug_log),
        "state": str(state_path),
        "run_started_at": iso(run_start),
        "verify_started_at": iso(verify_start),
        "api_request_turns": api_turns,
        "wall_seconds": round(wall_seconds, 3),
        "window_count": len(windows),
        "covered_span_count": len(covered),
        "windows": [
            {"start": iso(start), "end": iso(end), "seconds": round((end - start).total_seconds(), 3)}
            for start, end in windows
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
