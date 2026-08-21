#!/usr/bin/env python3
"""Normalize raw pair-JUDGE stdout into canonical VERIFY JSONL."""

from __future__ import annotations

import argparse
import json
import pathlib
import runpy
import sys
import tempfile
from typing import Any


MERGE_CONTRACT = runpy.run_path(pathlib.Path(__file__).with_name("verify-merge-findings.py"))
PARSER = runpy.run_path(pathlib.Path(__file__).with_name("judge-output-parser.py"))
VERDICT_RANK = MERGE_CONTRACT["VERDICT_RANK"]
finding_rank = MERGE_CONTRACT["finding_rank"]


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str) -> Any:
    return json.loads(text, parse_constant=reject_json_constant)


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        tmp_name = handle.name
    pathlib.Path(tmp_name).replace(path)


def collect_text(
    text: str, source: pathlib.Path
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    findings, summary = PARSER["collect_text"](text, source)
    if findings and summary is None:
        raise SystemExit("error: findings without terminal verdict")
    if summary is not None and summary["verdict"] == "PASS" and any(finding_rank(finding) == 2 for finding in findings):
        raise SystemExit("error: verdict-binding finding cannot have a PASS verdict")
    if not findings and (summary is None or summary.get("verdict") != "PASS"):
        raise SystemExit("error: non-PASS verdict without JSONL findings")
    return findings, summary


def collect_stdout(stdout_path: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    findings, summary = PARSER["collect_stdout"](stdout_path)
    if findings and summary is None:
        raise SystemExit("error: findings without terminal verdict")
    if summary is not None and summary["verdict"] == "PASS" and any(finding_rank(finding) == 2 for finding in findings):
        raise SystemExit("error: verdict-binding finding cannot have a PASS verdict")
    if not findings and (summary is None or summary.get("verdict") != "PASS"):
        raise SystemExit("error: non-PASS verdict without JSONL findings")
    return findings, summary


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        stdout_path = root / "pair-judge.stdout"
        out_path = root / "verify.pair.findings.jsonl"
        summary_path = root / "pair-judge.summary.json"

        def assert_rejected(text: str, label: str, *message_parts: str) -> None:
            stdout_path.write_text(text, encoding="utf-8")
            try:
                collect_stdout(stdout_path)
            except SystemExit as exc:
                message = str(exc)
                assert all(part in message for part in message_parts)
            else:
                raise AssertionError(f"{label} must be rejected")

        plain_finding = {"id": "a", "severity": "HIGH"}
        plain_summary = {"verdict": "NEEDS_WORK"}
        stdout_path.write_text(
            json.dumps(plain_finding) + "\n"
            + plain_summary["verdict"] + "\n",
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == [plain_finding]
        assert summary == plain_summary
        write_outputs(findings, summary, out_path, summary_path)
        assert out_path.read_text(encoding="utf-8").count("\n") == 1
        assert loads_strict_json(summary_path.read_text(encoding="utf-8"))["verdict"] == "NEEDS_WORK"
        assert_rejected(
            '{"id":"nan","severity":NaN}\n',
            "NaN pair-JUDGE stdout finding",
            "invalid JSON numeric constant: NaN",
        )
        rejection_cases = (
            ("", "no verdict line", "non-PASS verdict without JSONL findings"),
            (json.dumps(plain_finding) + "\n", "finding without terminal verdict", "findings without terminal verdict"),
            ('{"verdict":"pass"}\n', "lowercase pass", "finding missing valid severity"),
            ('{"verdict":"UNKNOWN"}\n', "unknown verdict", "finding missing valid severity"),
        )
        for text, label, message in rejection_cases:
            assert_rejected(
                text,
                label,
                message,
            )

        def envelope(text: Any, stop_reason: str = "EndTurn") -> str:
            return json.dumps(
                {
                    "text": text,
                    "stopReason": stop_reason,
                    "sessionId": "session",
                    "requestId": "request",
                }
            )

        envelope_finding = {
            "id": "envelope-finding",
            "severity": "HIGH",
            "detail": {"preserved": True},
        }
        envelope_summary = {"verdict": "NEEDS_WORK"}
        stdout_path.write_text(
            envelope(
                json.dumps(envelope_finding)
                + "\n" + envelope_summary["verdict"] + "\n"
            ),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == [envelope_finding]
        assert summary == envelope_summary

        assert_rejected(
            envelope("review completed without findings"),
            "findings-less envelope text",
            "invalid JSONL",
        )
        assert_rejected(
            envelope('{"findings":[],"verdict":"PASS"}', "Cancelled"),
            "Cancelled envelope",
            "envelope stopReason must be 'EndTurn'",
            "'Cancelled'",
        )
        assert_rejected(
            envelope("", "UnknownStop"),
            "unknown envelope stopReason",
            "envelope stopReason must be 'EndTurn'",
            "'UnknownStop'",
        )
        assert_rejected(
            envelope(None),
            "non-string envelope text",
            "error: envelope text must be a string",
        )
        assert_rejected(
            envelope("I will inspect the result.\n" + envelope_summary["verdict"] + "\n"),
            "narrative envelope preamble",
            "invalid JSONL",
        )
        dual_document = (
            json.dumps(envelope_finding)
            + json.dumps({"id": "second", "severity": "LOW"})
            + "\n" + envelope_summary["verdict"] + "\n"
        )
        assert_rejected(
            envelope(dual_document),
            "concatenated envelope documents",
            "invalid JSONL",
        )
        clean_summary = {"verdict": "PASS"}
        stdout_path.write_text(
            envelope(clean_summary["verdict"] + "\n"),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == []
        assert summary == clean_summary
        stdout_path.write_text(
            json.dumps(
                {
                    "type": "system",
                    "text": clean_summary["verdict"] + "\n",
                    "stopReason": "EndTurn",
                    "sessionId": "session",
                    "requestId": "request",
                }
            ),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == []
        assert summary == clean_summary

        # R4: a valid plain finding may carry an unrelated `type` field. A
        # first-line `type: system` finding is not a stream discriminator.
        system_finding = {"id": "system-finding", "severity": "LOW", "type": "system"}
        stdout_path.write_text(
            json.dumps(system_finding) + "\n" + clean_summary["verdict"] + "\n",
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == [system_finding]
        assert summary == clean_summary

        # iter-0106 — Grok whole-message NDJSON carrier (R2/R3).
        def init_record(session: str = "s1") -> dict[str, Any]:
            return {"type": "system", "subtype": "init", "session_id": session, "model": "grok-build"}

        def assistant_record(
            blocks: list[Any], stop_reason: str = "end_turn", session: str = "s1"
        ) -> dict[str, Any]:
            return {
                "type": "assistant",
                "message": {"id": "msg", "role": "assistant", "content": blocks, "stop_reason": stop_reason},
                "parent_tool_use_id": None,
                "session_id": session,
            }

        def result_record(
            text: str,
            session: str = "s1",
            subtype: str = "success",
            is_error: Any = False,
            stop_reason: str = "end_turn",
        ) -> dict[str, Any]:
            return {
                "type": "result",
                "subtype": subtype,
                "is_error": is_error,
                "result": text,
                "stop_reason": stop_reason,
                "session_id": session,
            }

        def text_block(value: str) -> dict[str, Any]:
            return {"type": "text", "text": value}

        def stream(*records: Any) -> str:
            return "".join(json.dumps(record) + "\n" for record in records)

        pass_text = "PASS\n"
        stdout_path.write_text(
            stream(init_record(), assistant_record([text_block(pass_text)]), result_record(pass_text)),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == []
        assert summary == {"verdict": "PASS"}

        # A real tool turn precedes the contract, and the terminal message arrives
        # as two text blocks whose in-order concatenation is the result text.
        stream_finding = {"id": "stream-finding", "severity": "HIGH"}
        head = json.dumps(stream_finding) + "\n"
        tail = "# SUMMARY " + json.dumps({"verdict": "NEEDS_WORK"}) + "\n"
        contract = head + tail
        narration = assistant_record(
            [
                text_block("Let me read the file."),
                {"type": "tool_use", "id": "call_1", "name": "read_file", "input": {"path": "src/main.rs"}},
            ],
            stop_reason="tool_use",
        )
        tool_result = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "fn main() {}"}],
            },
            "parent_tool_use_id": None,
            "session_id": "s1",
        }
        stdout_path.write_text(
            stream(
                init_record(),
                narration,
                tool_result,
                assistant_record([text_block(head), text_block(tail)]),
                result_record(contract),
            ),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == [stream_finding]
        assert summary == {"verdict": "NEEDS_WORK"}

        # The welded body is exactly the shape envelope recovery accepts, so this
        # also proves the stream branch never falls through to that recovery.
        welded = "I reviewed the diff.\n" + contract
        stream_rejections = (
            (
                stream(init_record(), assistant_record([text_block(welded)]), result_record(welded)),
                "narration welded into the terminal message",
                "invalid JSONL",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(contract)]),
                    assistant_record([text_block(contract)]),
                    result_record(contract),
                ),
                "two terminal end_turn messages",
                "exactly one final end_turn assistant message",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(contract)]),
                    assistant_record([text_block("more")], stop_reason="tool_use"),
                    result_record(contract),
                ),
                "end_turn message that is not the final assistant message",
                "exactly one final end_turn assistant message",
            ),
            (
                # The malformed line is the only defect: skipping it leaves a valid stream.
                stream(init_record(), assistant_record([text_block(pass_text)]))
                + '{"type":"assistant"\n'
                + stream(result_record(pass_text)),
                "malformed stream NDJSON inside an otherwise valid stream",
                "invalid stream NDJSON",
            ),
            (
                stream(init_record(), assistant_record([text_block(pass_text)])),
                "stream without a terminal result",
                "exactly one terminal result",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text),
                    tool_result,
                ),
                "data after the terminal result",
                "exactly one terminal result",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    tool_result,
                    result_record(pass_text),
                ),
                "data between the terminal assistant and result",
                "exactly one final end_turn assistant message",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text, subtype="error_during_execution"),
                ),
                "error result subtype",
                "not a successful end_turn",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text, stop_reason="cancelled"),
                ),
                "cancelled result",
                "not a successful end_turn",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text, is_error=True),
                ),
                "error-flagged result",
                "not a successful end_turn",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    result_record("NEEDS_WORK\n"),
                ),
                "result text that disagrees with the terminal message",
                "result text does not match the terminal message",
            ),
            (
                stream(
                    init_record(),
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text, session="s2"),
                ),
                "result from another session",
                "session identity does not agree",
            ),
            (
                stream(
                    init_record(),
                    {"type": "stream_event", "event": {"type": "content_block_delta"}, "session_id": "s1"},
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text),
                ),
                "partial-message frame",
                "unknown stream record",
            ),
            (
                stream(
                    init_record(),
                    {"type": "system", "subtype": "compact_boundary", "session_id": "s1"},
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text),
                ),
                "compact boundary",
                "second system record",
            ),
            (
                stream(
                    init_record(),
                    {"type": "unknown", "session_id": "s1"},
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text),
                ),
                "unknown record type",
                "unknown stream record",
            ),
            (
                stream(
                    {"type": "system", "subtype": "compact_boundary", "session_id": "s1"},
                    assistant_record([text_block(pass_text)]),
                    result_record(pass_text),
                ),
                "stream that does not open with system/init",
                "must open with system/init",
            ),
        )
        for text, label, message in stream_rejections:
            assert_rejected(text, label, message)
    return 0


def write_outputs(
    findings: list[dict[str, Any]],
    summary: dict[str, Any] | None,
    out_path: pathlib.Path,
    summary_path: pathlib.Path,
) -> None:
    atomic_write(
        out_path,
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in findings),
    )
    if summary is not None:
        atomic_write(summary_path, json.dumps(summary, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devlyn-dir", default=".devlyn")
    parser.add_argument("--stdout-file", default="pair-judge.stdout")
    parser.add_argument("--out", default="verify.pair.findings.jsonl")
    parser.add_argument("--summary-out", default="pair-judge.summary.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    devlyn = pathlib.Path(args.devlyn_dir)
    stdout_path = devlyn / args.stdout_file
    if not stdout_path.is_file():
        sys.stderr.write(f"error: {stdout_path} not found\n")
        return 1
    findings, summary = collect_stdout(stdout_path)
    write_outputs(findings, summary, devlyn / args.out, devlyn / args.summary_out)
    print(json.dumps({"findings_count": len(findings), "summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
