#!/usr/bin/env python3
"""Normalize raw pair-JUDGE stdout into canonical VERIFY JSONL."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any


FINDING_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
ENVELOPE_KEYS = {"text", "stopReason", "sessionId", "requestId"}


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


def collect(stdout_path: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    findings: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    with stdout_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            raw = line.strip()
            if not raw:
                continue
            if raw.startswith("# SUMMARY "):
                try:
                    item = loads_strict_json(raw.removeprefix("# SUMMARY ").strip())
                except ValueError as exc:
                    raise SystemExit(f"error: invalid SUMMARY JSON at {stdout_path}:{line_no}: {exc}")
                if not isinstance(item, dict):
                    raise SystemExit(f"error: SUMMARY is not an object at {stdout_path}:{line_no}")
                summary = item
                continue
            if raw.startswith("#"):
                continue
            try:
                item = loads_strict_json(raw)
            except ValueError as exc:
                raise SystemExit(f"error: invalid JSONL at {stdout_path}:{line_no}: {exc}")
            if not isinstance(item, dict):
                raise SystemExit(f"error: JSONL item is not an object at {stdout_path}:{line_no}")
            severity = str(item.get("severity") or "").upper()
            if severity not in FINDING_SEVERITIES:
                raise SystemExit(f"error: finding missing valid severity at {stdout_path}:{line_no}")
            findings.append(item)
    if not findings and (summary is None or summary.get("verdict") != "PASS"):
        raise SystemExit("error: non-PASS SUMMARY without JSONL findings")
    return findings, summary


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
        return collect(stdout_path)

    stop_reason = candidate["stopReason"]
    if stop_reason != "EndTurn":
        raise SystemExit(
            f"error: envelope stopReason must be 'EndTurn' at {stdout_path}; "
            f"got {stop_reason!r}"
        )
    envelope_text = candidate["text"]
    if not isinstance(envelope_text, str):
        raise SystemExit(f"error: envelope text must be a string at {stdout_path}")

    with tempfile.TemporaryDirectory() as tmp:
        text_path = pathlib.Path(tmp) / "envelope-text.stdout"
        text_path.write_text(envelope_text, encoding="utf-8")
        try:
            return collect(text_path)
        except SystemExit as exc:
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
            ("", "no SUMMARY line"),
            ('# SUMMARY {}\n', "empty SUMMARY object"),
            ('# SUMMARY {"verdict":"pass"}\n', "lowercase pass"),
            ('# SUMMARY {"verdict":"UNKNOWN"}\n', "unknown verdict"),
        )
        for text, label in rejection_cases:
            assert_rejected(
                text,
                label,
                "error: non-PASS SUMMARY without JSONL findings",
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
        assert_rejected(
            envelope(welded),
            "welded envelope preamble",
            "error: envelope text rejected: error: invalid JSONL",
        )
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
