#!/usr/bin/env python3
"""Normalize raw Codex pair-JUDGE stdout into canonical VERIFY JSONL."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any


FINDING_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


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
                    item = json.loads(raw.removeprefix("# SUMMARY ").strip())
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"error: invalid SUMMARY JSON at {stdout_path}:{line_no}: {exc}")
                if not isinstance(item, dict):
                    raise SystemExit(f"error: SUMMARY is not an object at {stdout_path}:{line_no}")
                summary = item
                continue
            if raw.startswith("#"):
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"error: invalid JSONL at {stdout_path}:{line_no}: {exc}")
            if not isinstance(item, dict):
                raise SystemExit(f"error: JSONL item is not an object at {stdout_path}:{line_no}")
            severity = str(item.get("severity") or "").upper()
            if severity not in FINDING_SEVERITIES:
                raise SystemExit(f"error: finding missing valid severity at {stdout_path}:{line_no}")
            findings.append(item)
    if not findings and summary is None:
        raise SystemExit("error: Codex pair-JUDGE stdout contained no JSONL findings or PASS line")
    if summary and summary.get("verdict") in {"NEEDS_WORK", "FAIL", "BLOCKED"} and not findings:
        raise SystemExit("error: non-PASS SUMMARY without JSONL findings")
    return findings, summary


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        stdout_path = root / "codex-judge.stdout"
        out_path = root / "verify.pair.findings.jsonl"
        summary_path = root / "codex-judge.summary.json"
        stdout_path.write_text(
            json.dumps({"id": "a", "severity": "HIGH"}) + "\n"
            + '# SUMMARY {"verdict":"NEEDS_WORK"}\n',
            encoding="utf-8",
        )
        findings, summary = collect(stdout_path)
        write_outputs(findings, summary, out_path, summary_path)
        assert out_path.read_text(encoding="utf-8").count("\n") == 1
        assert json.loads(summary_path.read_text(encoding="utf-8"))["verdict"] == "NEEDS_WORK"
        stdout_path.write_text("", encoding="utf-8")
        try:
            collect(stdout_path)
        except SystemExit as exc:
            assert "no JSONL findings" in str(exc)
        else:
            raise AssertionError("empty Codex stdout must not normalize to PASS")
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
    parser.add_argument("--stdout-file", default="codex-judge.stdout")
    parser.add_argument("--out", default="verify.pair.findings.jsonl")
    parser.add_argument("--summary-out", default="codex-judge.summary.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    devlyn = pathlib.Path(args.devlyn_dir)
    stdout_path = devlyn / args.stdout_file
    if not stdout_path.is_file():
        sys.stderr.write(f"error: {stdout_path} not found\n")
        return 1
    findings, summary = collect(stdout_path)
    write_outputs(findings, summary, devlyn / args.out, devlyn / args.summary_out)
    print(json.dumps({"findings_count": len(findings), "summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
