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


FINDING_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
ENVELOPE_KEYS = {"text", "stopReason", "sessionId", "requestId"}
IGNORABLE_FENCES = {"```", "```json", "```jsonl"}
MERGE_CONTRACT = runpy.run_path(pathlib.Path(__file__).with_name("verify-merge-findings.py"))
VERDICT_RANK = MERGE_CONTRACT["VERDICT_RANK"]
finding_rank = MERGE_CONTRACT["finding_rank"]
NARRATIVE_PREAMBLE_BYTES = frozenset(
    b"\t\n\r !\"$%&'()*+,-./0123456789:;<=>?@"
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_abcdefghijklmnopqrstuvwxyz|}~"
) | frozenset(range(0x80, 0x100))


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
    findings: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        raw = line.strip()
        if not raw or raw in IGNORABLE_FENCES:
            continue
        if raw.startswith("# SUMMARY "):
            if summary is not None:
                raise SystemExit(f"error: record after terminal SUMMARY at {source}:{line_no}")
            try:
                item = loads_strict_json(raw.removeprefix("# SUMMARY ").strip())
            except ValueError as exc:
                raise SystemExit(f"error: invalid SUMMARY JSON at {source}:{line_no}: {exc}")
            if not isinstance(item, dict):
                raise SystemExit(f"error: SUMMARY is not an object at {source}:{line_no}")
            if item.get("verdict") not in VERDICT_RANK:
                raise SystemExit(f"error: SUMMARY has unknown verdict at {source}:{line_no}")
            summary = item
            continue
        if raw.startswith("#"):
            continue
        if summary is not None:
            raise SystemExit(f"error: record after terminal SUMMARY at {source}:{line_no}")
        try:
            item = loads_strict_json(raw)
        except ValueError as exc:
            raise SystemExit(f"error: invalid JSONL at {source}:{line_no}: {exc}")
        if not isinstance(item, dict):
            raise SystemExit(f"error: JSONL item is not an object at {source}:{line_no}")
        if set(item) == {"verdict"}:
            if item["verdict"] not in VERDICT_RANK:
                raise SystemExit(f"error: SUMMARY has unknown verdict at {source}:{line_no}")
            summary = item
            continue
        severity = str(item.get("severity") or "").upper()
        if severity not in FINDING_SEVERITIES:
            raise SystemExit(f"error: finding missing valid severity at {source}:{line_no}")
        findings.append(item)
    if summary is not None and summary["verdict"] == "PASS" and any(
        finding_rank(finding) == 2 for finding in findings
    ):
        raise SystemExit("error: verdict-binding finding cannot have a PASS SUMMARY")
    if not findings and (summary is None or summary.get("verdict") != "PASS"):
        raise SystemExit("error: non-PASS SUMMARY without JSONL findings")
    return findings, summary


def recover_envelope_text(
    text: str, source: pathlib.Path
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    encoded = text.encode("utf-8")
    for cut, byte in enumerate(encoded[:-1], 1):
        if byte not in NARRATIVE_PREAMBLE_BYTES:
            break
        try:
            candidate = encoded[cut:].decode("utf-8")
        except UnicodeDecodeError:
            continue
        try:
            findings, summary = collect_text(candidate, source)
        except SystemExit:
            continue
        if (
            summary is not None
            and summary["verdict"] == "NEEDS_WORK"
            and any(finding_rank(finding) == 2 for finding in findings)
        ):
            return findings, summary
    raise SystemExit("error: no admissible envelope recovery")


def collect_stdout(stdout_path: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    stdout_text = stdout_path.read_text(encoding="utf-8")
    try:
        candidate = loads_strict_json(stdout_text)
    except ValueError:
        candidate = None
    if (
        not isinstance(candidate, dict)
        or not ENVELOPE_KEYS.issubset(candidate)
        or "severity" in candidate
    ):
        return collect_text(stdout_text, stdout_path)

    stop_reason = candidate["stopReason"]
    if stop_reason != "EndTurn":
        raise SystemExit(
            f"error: envelope stopReason must be 'EndTurn' at {stdout_path}; "
            f"got {stop_reason!r}"
        )
    envelope_text = candidate["text"]
    if not isinstance(envelope_text, str):
        raise SystemExit(f"error: envelope text must be a string at {stdout_path}")

    try:
        return collect_text(envelope_text, stdout_path)
    except SystemExit as exc:
        try:
            return recover_envelope_text(envelope_text, stdout_path)
        except SystemExit:
            raise SystemExit(f"error: envelope text rejected: {exc}") from None


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
            + "# SUMMARY " + json.dumps(plain_summary) + "\n",
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
            ("", "no SUMMARY line", "non-PASS SUMMARY without JSONL findings"),
            ('# SUMMARY {}\n', "empty SUMMARY object", "SUMMARY has unknown verdict"),
            ('# SUMMARY {"verdict":"pass"}\n', "lowercase pass", "SUMMARY has unknown verdict"),
            ('# SUMMARY {"verdict":"UNKNOWN"}\n', "unknown verdict", "SUMMARY has unknown verdict"),
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
                + "\n# SUMMARY "
                + json.dumps(envelope_summary)
                + "\n"
            ),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == [envelope_finding]
        assert summary == envelope_summary

        assert_rejected(
            envelope("review completed without findings"),
            "findings-less envelope text",
            "error: envelope text rejected: error: invalid JSONL",
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
        welded = (
            "I will inspect the result."
            + json.dumps(envelope_finding)
            + "\n# SUMMARY "
            + json.dumps(envelope_summary)
            + "\n"
        )
        stdout_path.write_text(envelope(welded), encoding="utf-8")
        findings, summary = collect_stdout(stdout_path)
        assert findings == [envelope_finding]
        assert summary == envelope_summary
        dual_document = (
            json.dumps(envelope_finding)
            + json.dumps({"id": "second", "severity": "LOW"})
            + "\n# SUMMARY "
            + json.dumps(envelope_summary)
            + "\n"
        )
        assert_rejected(
            envelope(dual_document),
            "concatenated envelope documents",
            "error: envelope text rejected: error: invalid JSONL",
        )
        clean_summary = {"verdict": "PASS"}
        stdout_path.write_text(
            envelope("# SUMMARY " + json.dumps(clean_summary) + "\n"),
            encoding="utf-8",
        )
        findings, summary = collect_stdout(stdout_path)
        assert findings == []
        assert summary == clean_summary
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
