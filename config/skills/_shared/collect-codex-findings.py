#!/usr/bin/env python3
"""Normalize raw pair-JUDGE stdout into canonical VERIFY JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import runpy
import sys
import tempfile
from typing import Any


PARSER = runpy.run_path(pathlib.Path(__file__).with_name("judge-output-parser.py"))
VERDICT_RANK = PARSER["VERDICT_RANK"]
finding_rank = PARSER["finding_rank"]
collect_stdout = PARSER["collect_judge"]


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict_json(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=reject_json_constant,
        object_pairs_hook=reject_duplicate_keys,
    )


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        tmp_name = handle.name
    pathlib.Path(tmp_name).replace(path)


OBSERVED_S6_16_R0 = (  # 0225 replay s6-16-r0 claude-judge.r0.stdout, exact bytes (no final newline)
    'I found no blocking issues, only two low-severity ones.\n'
    '\n'
    '{"id":"F1","rule_id":"design.duplicated-logic","severity":"LOW","file":"bin/devlyn.js","line":713,"message":"The deprecated-path list is rebuilt inline instead of reusing `cleanupDeprecated` (bin/devlyn.js:341-361), which is still used at line 904: `...DEPRECATED_FILES.map((relPath) => path.join(agentDir, relPath)), ...DEPRECATED_DIRS.map((relPath) => skillPath(path.join(agentDir, \'skills\'), path.basename(relPath)))`. Both places now build the same list, so a future change to one can miss the other.","criterion_ref":"Requirements: perform the same deprecated cleanup","confidence":"medium"}\n'
    '{"id":"F2","rule_id":"consistency.behavior-drift","severity":"LOW","file":"bin/devlyn.js","line":728,"message":"Deprecated cleanup behaves slightly differently from the original. The original used `fs.existsSync(fullPath)`, which follows symlinks, and logged files as `✕ ${relPath} (deprecated)` and directories as `✕ ${relPath}/ (removed)`. The new `moveAside` checks with `fs.lstatSync(target, { throwIfNoEntry: false })`, so it also removes dangling symlinks at deprecated paths, and it logs every entry as `✕ ${path.relative(agentDir, fullPath)} (removed)`. Both changes are small, but they are not literally \'the same deprecated cleanup\'.","criterion_ref":"Requirements: perform the same deprecated cleanup","confidence":"low"}\n'
    'PASS_WITH_ISSUES'
)


def self_test() -> int:
    try:
        loads_strict_json('{"verdict":"PASS","verdict":"BLOCKED"}')
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate judge result key was accepted")
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
        assert_rejected(
            '# SUMMARY {"verdict":"PASS","verdict":"BLOCKED"}\n',
            "duplicate pair-JUDGE summary verdict",
            "duplicate JSON key: verdict",
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
            "verdict-less envelope narrative",
            "non-PASS verdict without JSONL findings",
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
            "narrative preamble before a findings-less NEEDS_WORK",
            "non-PASS verdict without JSONL findings",
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

        # 0225 — one leading-narrative rule for both seats: narrative before the first record or fence
        # carries no authority and is skipped; every other non-record line still rejects. The first case is
        # the exact s6-16-r0 replay capture (Claude primary), which the pre-0225 contract BLOCKED.
        observed = OBSERVED_S6_16_R0.encode("utf-8")
        assert len(observed) == 1409 and hashlib.sha256(observed).hexdigest() == (
            "328a03681a30ef0ab8da4e3d0e7361f926078b7d0c8a700f786caf38ac7c0405")
        observed_findings = [loads_strict_json(line) for line in OBSERVED_S6_16_R0.splitlines()[2:4]]
        high = json.dumps({"id": "h", "severity": "HIGH"})
        info = json.dumps({"id": "i", "severity": "INFO"})
        binding_medium = json.dumps({"id": "m", "severity": "MEDIUM", "verdict_binding": True})
        accepted = (
            ("P-observed-s6-16-r0", OBSERVED_S6_16_R0, observed_findings, "PASS_WITH_ISSUES"),
            ("P-leading-clean-PASS", "I reviewed every clause and the sealed evidence.\nPASS\n", [], "PASS"),
            ("P-leading-binding-NEEDS_WORK", f"Two notes follow.\n\n{high}\nNEEDS_WORK\n",
             [loads_strict_json(high)], "NEEDS_WORK"),
            ("P-leading-Unicode-CRLF", f"Überprüft: zwei Hinweise.\r\n{high}\r\nNEEDS_WORK\r\n",
             [loads_strict_json(high)], "NEEDS_WORK"),
            ("P-inline-W1", f"Running the probe and comparing the output.{high}\nNEEDS_WORK\n",
             [loads_strict_json(high)], "NEEDS_WORK"),
            ("P-SUMMARY", f"Summary below.\n{high}\n# SUMMARY {{\"verdict\":\"NEEDS_WORK\"}}\n",
             [loads_strict_json(high)], "NEEDS_WORK"),
            ("P-legacy-advisory-PASS", f"{info}\nPASS\n", [loads_strict_json(info)], "PASS"),
        )
        for label, text, want_findings, want_verdict in accepted:
            for ingress, body in (("raw", text), ("envelope", envelope(text))):
                stdout_path.write_text(body, encoding="utf-8", newline="")
                findings, summary = collect_stdout(stdout_path)
                assert (findings, summary) == (want_findings, {"verdict": want_verdict}), (label, ingress)
        rejected = (
            # N-json-looking: a record-shaped line that is not a valid finding.
            ("N-malformed-object", f"Notes.\n{{\"id\": \"x\"\n{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-array", f"Notes.\n[{high}]\nNEEDS_WORK\n", "not an object"),
            ("N-scalar", "true\nPASS\n", "not an object"),
            ("N-duplicate-keys", 'Notes.\n{"id":"a","id":"b","severity":"HIGH"}\nNEEDS_WORK\n', "duplicate JSON key"),
            ("N-nan", 'Notes.\n{"id":"a","severity":"HIGH","line":NaN}\nNEEDS_WORK\n', "NaN"),
            ("N-invalid-severity", 'Notes.\n{"id":"a","severity":"URGENT"}\nNEEDS_WORK\n', "valid severity"),
            ("N-concatenated", f"Notes.\n{high}{high}\nNEEDS_WORK\n", "invalid JSONL"),
            # N-verdict.
            ("N-missing-verdict", f"Notes.\n{high}\n", "findings without terminal verdict"),
            ("N-duplicate-verdict", f"Notes.\n{high}\nNEEDS_WORK\nNEEDS_WORK\n", "record after terminal verdict"),
            ("N-unknown-summary", f"Notes.\n{high}\n# SUMMARY {{\"verdict\":\"MAYBE\"}}\n", "unknown value"),
            ("N-non-PASS-without-findings", "Nothing to add.\nNEEDS_WORK\n", "non-PASS verdict without JSONL findings"),
            ("N-HIGH-with-PASS", f"Notes.\n{high}\nPASS\n", "cannot have a PASS verdict"),
            ("N-binding-MEDIUM-with-PASS", f"Notes.\n{binding_medium}\nPASS\n", "cannot have a PASS verdict"),
            # N-authority-prefix: a leading line that could carry authority is not narrative.
            ("N-verdict-word-prefix", "This review would pass.\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-lone-identifier-prefix", f"LGTM\n{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-commented-finding-prefix", f"# {high}\n{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-malformed-fence-prefix", f"```python\n{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-bad-welded-prefix", f"Result is PASS.{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-fenced-welded-prefix", f"Notes```json{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-malformed-first-object", f'Notes.{{"id":"a"\n{high}\nNEEDS_WORK\n', "invalid JSONL"),
            # N-interleaved-prose and N-after-terminal: narrative ends at the first record or fence.
            ("N-interleaved-prose", f"{high}\nOne more note.\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-prose-after-fence", f"```\nNotes.\n{high}\nNEEDS_WORK\n", "invalid JSONL"),
            ("N-prose-after-verdict", f"{high}\nNEEDS_WORK\nThat is all.\n", "record after terminal verdict"),
            ("N-finding-after-verdict", f"{high}\nNEEDS_WORK\n{high}\n", "record after terminal verdict"),
        )
        for label, text, message in rejected:
            for body in (text, envelope(text)):
                assert_rejected(body, label, message)

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

        # 0225: the terminal message follows the same leading-narrative rule as every other ingress.
        welded = "I reviewed the diff.\n" + contract
        stdout_path.write_text(
            stream(init_record(), assistant_record([text_block(welded)]), result_record(welded)), encoding="utf-8")
        assert collect_stdout(stdout_path) == ([stream_finding], {"verdict": "NEEDS_WORK"})
        stdout_path.write_text(stream(init_record(), assistant_record([text_block(OBSERVED_S6_16_R0)]),
                                      result_record(OBSERVED_S6_16_R0)), encoding="utf-8")
        assert collect_stdout(stdout_path) == (observed_findings, {"verdict": "PASS_WITH_ISSUES"})
        stream_rejections = (
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
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
