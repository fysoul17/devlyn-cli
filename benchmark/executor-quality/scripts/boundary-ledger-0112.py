#!/usr/bin/env python3
"""iter-0112 request-level boundary ledger collector."""
import argparse
import json
import pathlib
import tempfile


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rows.append(json.loads(line))
    return rows


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def invalid_boundary(row, reason):
    return {
        "position_index": row.get("position_index"),
        "task": row.get("task"),
        "records_invalid": True,
        "invalid_reasons": [reason],
        "usage_entries": [],
        "requests": [],
        "unique_request_count": 0,
        "peak_effective_context": None,
        "inferred_compaction": False,
    }


def validate_custody(custody):
    try:
        links = custody["links"]
    except (KeyError, TypeError):
        return [], "custody links missing", 1
    if not isinstance(links, list):
        return [], "custody links malformed", 1
    expected_resume = None
    valid_links = []
    for position_index, link in enumerate(links, start=1):
        if not isinstance(link, dict):
            return valid_links, "custody link malformed", position_index
        launched = link.get("launched_resume_id")
        reported = link.get("reported_session_id")
        if link.get("position_index") != position_index or launched != expected_resume:
            return valid_links, "custody link discontinuity", position_index
        if not isinstance(reported, str) or not reported:
            return valid_links, "custody reported session id missing", position_index
        valid_links.append(link)
        expected_resume = reported
    return valid_links, None, None


def snapshot_window(boundary):
    before = boundary.get("before")
    after = boundary.get("after")
    transcript_dir = boundary.get("transcript_dir")
    if not isinstance(before, dict) or not isinstance(after, dict) or not isinstance(transcript_dir, str):
        raise ValueError("snapshot window malformed")
    if set(before) - set(after):
        raise ValueError("snapshot file missing after invocation")
    root = pathlib.Path(transcript_dir)
    windows = []
    for filename, after_size in sorted(after.items()):
        before_size = before.get(filename, 0)
        if not isinstance(filename, str) or pathlib.PurePath(filename).name != filename or not filename.endswith(".jsonl"):
            raise ValueError("snapshot filename malformed")
        if type(before_size) is not int or type(after_size) is not int or before_size < 0 or after_size < before_size:
            raise ValueError("snapshot size malformed")
        path = root / filename
        try:
            current_size = path.stat().st_size
            if not path.is_file() or current_size < after_size:
                raise ValueError("snapshot window unresolved")
            windows.append((filename, path.read_bytes()[before_size:after_size]))
        except OSError as exc:
            raise ValueError("snapshot window unresolved") from exc
    return windows


def usage_for_entry(entry):
    message = entry.get("message")
    usage = message.get("usage") if isinstance(message, dict) else None
    if not isinstance(usage, dict):
        return None
    request_id = entry.get("requestId")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("usage entry lacks requestId")
    if "input_tokens" not in usage:
        raise ValueError("usage input_tokens missing")
    tokens = []
    for name in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        value = usage[name] if name == "input_tokens" else usage.get(name, 0)
        if type(value) is not int or value < 0:
            raise ValueError("usage token field malformed")
        tokens.append(value)
    return request_id, sum(tokens)


def collect_boundary(row, boundary, custody_links, custody_error, custody_break_at, previous_peak, seen_requests):
    position_index = row.get("position_index")
    if type(position_index) is not int or position_index < 1:
        return invalid_boundary(row, "row position malformed")
    if custody_error is not None and position_index >= custody_break_at:
        return invalid_boundary(row, custody_error)
    if position_index > len(custody_links):
        return invalid_boundary(row, "custody broken before boundary")
    link = custody_links[position_index - 1]
    if not row.get("custody_ok") or row.get("custody_broken"):
        return invalid_boundary(row, "driver marked custody invalid")
    if (
        row.get("launched_resume_id") != link.get("launched_resume_id")
        or row.get("reported_session_id") != link.get("reported_session_id")
        or boundary.get("launched_resume_id") != link.get("launched_resume_id")
    ):
        return invalid_boundary(row, "row and custody link disagree")
    reachable = set()
    for custody_link in custody_links[:position_index]:
        launched = custody_link["launched_resume_id"]
        if launched is not None:
            reachable.add(launched)
        reachable.add(custody_link["reported_session_id"])
    usage_entries = []
    requests = {}
    try:
        for filename, payload in snapshot_window(boundary):
            for raw_line in payload.splitlines():
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ValueError("unparseable JSONL line") from exc
                if not isinstance(entry, dict):
                    raise ValueError("transcript entry malformed")
                session_id = entry.get("sessionId")
                if not isinstance(session_id, str) or session_id not in reachable:
                    raise ValueError("foreign session id in transcript window")
                usage = usage_for_entry(entry)
                if usage is None:
                    continue
                request_id, effective_context = usage
                usage_entry = {
                    "filename": filename,
                    "request_id": request_id,
                    "session_id": session_id,
                    "effective_context": effective_context,
                }
                existing = requests.get(request_id)
                if existing is not None and existing != effective_context:
                    raise ValueError("requestId has conflicting usage")
                seen = seen_requests.get(request_id)
                if seen is not None:
                    if seen != effective_context:
                        raise ValueError("requestId has conflicting usage")
                    usage_entry["carried"] = True
                elif existing is None:
                    requests[request_id] = effective_context
                seen_requests[request_id] = effective_context
                usage_entries.append(usage_entry)
    except ValueError as exc:
        result = invalid_boundary(row, str(exc))
        result["usage_entries"] = usage_entries
        return result
    if not requests:
        return invalid_boundary(row, "zero usage-bearing entries")
    peak = max(requests.values())
    rotated = position_index > 1 and link["launched_resume_id"] != link["reported_session_id"]
    return {
        "position_index": position_index,
        "task": row.get("task"),
        "records_invalid": False,
        "invalid_reasons": [],
        "usage_entries": usage_entries,
        "requests": [
            {"request_id": request_id, "effective_context": effective_context}
            for request_id, effective_context in sorted(requests.items())
        ],
        "unique_request_count": len(requests),
        "peak_effective_context": peak,
        "inferred_compaction": (previous_peak is not None and peak < previous_peak) or rotated,
    }


def collect(session_dir):
    custody = read_json(session_dir / "custody.json")
    boundaries = read_json(session_dir / "boundaries.json")
    rows = read_rows(session_dir / "rows.jsonl")
    if not isinstance(boundaries, list):
        raise ValueError("boundaries must be a list")
    by_position = {
        boundary.get("position_index"): boundary
        for boundary in boundaries
        if isinstance(boundary, dict) and isinstance(boundary.get("position_index"), int)
    }
    custody_links, custody_error, custody_break_at = validate_custody(custody)
    results = []
    previous_peak = None
    seen_requests = {}
    for row in sorted(rows, key=lambda item: item.get("position_index", 0)):
        if not isinstance(row, dict):
            raise ValueError("row malformed")
        boundary = by_position.get(row.get("position_index"))
        if boundary is None:
            result = invalid_boundary(row, "boundary record missing")
        else:
            result = collect_boundary(
                row, boundary, custody_links, custody_error, custody_break_at, previous_peak, seen_requests
            )
        results.append(result)
        if not result["records_invalid"]:
            previous_peak = result["peak_effective_context"]
    output = {
        "session_dir": str(session_dir),
        "boundaries": results,
    }
    write_json(session_dir / "boundary-ledger.json", output)
    return output


def transcript_line(session_id, request_id, input_tokens, cache_read_input_tokens=0, cache_creation_input_tokens=0):
    return json.dumps(
        {
            "sessionId": session_id,
            "requestId": request_id,
            "message": {
                "usage": {
                    "input_tokens": input_tokens,
                    "cache_read_input_tokens": cache_read_input_tokens,
                    "cache_creation_input_tokens": cache_creation_input_tokens,
                }
            },
        }
    ).encode("utf-8") + b"\n"


def self_test():
    with tempfile.TemporaryDirectory() as raw_dir:
        session_dir = pathlib.Path(raw_dir) / "session"
        transcript_dir = session_dir / "transcripts"
        transcript_dir.mkdir(parents=True)
        log = transcript_dir / "one.jsonl"
        first = transcript_line("s1", "request-1", 10, 3, 2)
        log.write_bytes(first + first)
        first_size = log.stat().st_size
        rotated_log = transcript_dir / "two.jsonl"
        second = transcript_line("s2", "request-2", 8)
        rotated_log.write_bytes(first + second)
        second_size = rotated_log.stat().st_size
        write_json(
            session_dir / "custody.json",
            {
                "links": [
                    {"position_index": 1, "launched_resume_id": None, "reported_session_id": "s1"},
                    {"position_index": 2, "launched_resume_id": "s1", "reported_session_id": "s2"},
                    {"position_index": 3, "launched_resume_id": "s2", "reported_session_id": "s3"},
                ]
            },
        )
        write_json(
            session_dir / "boundaries.json",
            [
                {"position_index": 1, "launched_resume_id": None, "transcript_dir": str(transcript_dir), "before": {}, "after": {"one.jsonl": first_size}},
                {"position_index": 2, "launched_resume_id": "s1", "transcript_dir": str(transcript_dir), "before": {"one.jsonl": first_size}, "after": {"one.jsonl": first_size, "two.jsonl": second_size}},
                {"position_index": 3, "launched_resume_id": "s2", "transcript_dir": str(transcript_dir), "before": {"one.jsonl": first_size, "two.jsonl": second_size}, "after": {"one.jsonl": first_size, "two.jsonl": second_size}},
            ],
        )
        rows = [
            {"position_index": 1, "task": "one", "custody_ok": True, "custody_broken": False, "launched_resume_id": None, "reported_session_id": "s1"},
            {"position_index": 2, "task": "two", "custody_ok": True, "custody_broken": False, "launched_resume_id": "s1", "reported_session_id": "s2"},
            {"position_index": 3, "task": "three", "custody_ok": True, "custody_broken": False, "launched_resume_id": "s2", "reported_session_id": "s3"},
        ]
        (session_dir / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        output = collect(session_dir)
        first_boundary, second_boundary, empty_boundary = output["boundaries"]
        assert first_boundary["unique_request_count"] == 1
        assert first_boundary["peak_effective_context"] == 15
        assert second_boundary["unique_request_count"] == 1
        assert second_boundary["peak_effective_context"] == 8
        assert second_boundary["usage_entries"][0]["carried"] is True
        assert second_boundary["inferred_compaction"] is True
        assert empty_boundary["records_invalid"] is True
        assert empty_boundary["invalid_reasons"] == ["zero usage-bearing entries"]
        broken = read_json(session_dir / "custody.json")
        broken["links"][1]["launched_resume_id"] = "unrelated-session"
        write_json(session_dir / "custody.json", broken)
        after_break = collect(session_dir)["boundaries"]
        assert after_break[0]["records_invalid"] is False
        assert all(boundary["records_invalid"] is True for boundary in after_break[1:])
        malformed_usage = json.loads(transcript_line("s1", "request-bool", 1).decode("utf-8"))
        malformed_usage["message"]["usage"]["input_tokens"] = True
        try:
            usage_for_entry(malformed_usage)
        except ValueError as exc:
            assert str(exc) == "usage token field malformed"
        else:
            raise AssertionError("boolean token count was accepted")
        try:
            snapshot_window(
                {
                    "transcript_dir": str(transcript_dir),
                    "before": {"one.jsonl": True},
                    "after": {"one.jsonl": first_size},
                }
            )
        except ValueError as exc:
            assert str(exc) == "snapshot size malformed"
        else:
            raise AssertionError("boolean snapshot size was accepted")
        invalid_dir = pathlib.Path(raw_dir) / "invalid-boundary"
        invalid_transcripts = invalid_dir / "transcripts"
        invalid_transcripts.mkdir(parents=True)
        first_log = transcript_line("s1", "r1", 10)
        invalid_log = transcript_line("s2", "r2", 100000) + b"not-json\n"
        replay_log = transcript_line("s3", "r2", 100000) + transcript_line("s3", "r3", 50)
        (invalid_transcripts / "one.jsonl").write_bytes(first_log)
        (invalid_transcripts / "two.jsonl").write_bytes(invalid_log)
        (invalid_transcripts / "three.jsonl").write_bytes(replay_log)
        write_json(
            invalid_dir / "custody.json",
            {"links": [
                {"position_index": 1, "launched_resume_id": None, "reported_session_id": "s1"},
                {"position_index": 2, "launched_resume_id": "s1", "reported_session_id": "s2"},
                {"position_index": 3, "launched_resume_id": "s2", "reported_session_id": "s3"},
            ]},
        )
        write_json(
            invalid_dir / "boundaries.json",
            [
                {"position_index": 1, "launched_resume_id": None, "transcript_dir": str(invalid_transcripts), "before": {}, "after": {"one.jsonl": len(first_log)}},
                {"position_index": 2, "launched_resume_id": "s1", "transcript_dir": str(invalid_transcripts), "before": {"one.jsonl": len(first_log)}, "after": {"one.jsonl": len(first_log), "two.jsonl": len(invalid_log)}},
                {"position_index": 3, "launched_resume_id": "s2", "transcript_dir": str(invalid_transcripts), "before": {"one.jsonl": len(first_log), "two.jsonl": len(invalid_log)}, "after": {"one.jsonl": len(first_log), "two.jsonl": len(invalid_log), "three.jsonl": len(replay_log)}},
            ],
        )
        (invalid_dir / "rows.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in [
                {"position_index": 1, "task": "one", "custody_ok": True, "custody_broken": False, "launched_resume_id": None, "reported_session_id": "s1"},
                {"position_index": 2, "task": "two", "custody_ok": True, "custody_broken": False, "launched_resume_id": "s1", "reported_session_id": "s2"},
                {"position_index": 3, "task": "three", "custody_ok": True, "custody_broken": False, "launched_resume_id": "s2", "reported_session_id": "s3"},
            ]),
            encoding="utf-8",
        )
        invalid_boundaries = collect(invalid_dir)["boundaries"]
        assert invalid_boundaries[1]["records_invalid"] is True
        assert invalid_boundaries[2]["peak_effective_context"] == 50
        assert invalid_boundaries[2]["usage_entries"][0]["carried"] is True
    print("PASS boundary-ledger-0112 self-test: dedup across valid and invalid boundaries, empty window, rotation, custody suffix invalidation, strict integers")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--session-dir")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.session_dir:
        parser.error("--session-dir is required unless --self-test is used")
    try:
        output = collect(pathlib.Path(args.session_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
