#!/usr/bin/env python3
"""Compute auto-resolve terminal verdict per references/pipeline-routing.md#terminal-state-algorithm.

Usage:
    python3 scripts/terminal_verdict.py [--devlyn-dir .devlyn] [--json]

Reads every `.devlyn/<phase>.findings.jsonl`, filters `status == "open"`, applies the
precedence list, and prints the verdict (stdout) and exit code.

Exit codes: 0 = PASS | 1 = PASS_WITH_ISSUES | 2 = NEEDS_WORK | 3 = BLOCKED

The pipeline routing file defines the authoritative precedence. This script implements
it deterministically so the orchestrator does not re-reason through the rule set per run.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter


PRECEDENCE = [
    # (label, predicate on finding list) — first True wins
    ("BLOCKED", lambda fs: any(f["severity"] == "CRITICAL" for f in fs)),
    ("NEEDS_WORK", lambda fs: any(
        f["severity"] == "HIGH"
        and any(f.get("rule_id", "").startswith(p) for p in ("correctness.", "security.", "design."))
        for f in fs
    )),
    ("NEEDS_WORK", lambda fs: any(f["severity"] == "HIGH" for f in fs)),
    ("NEEDS_WORK", lambda fs: any(
        f["severity"] == "MEDIUM" and f.get("rule_id", "").startswith("security.")
        for f in fs
    )),
    ("PASS_WITH_ISSUES", lambda fs: any(f["severity"] == "MEDIUM" for f in fs)),
    ("PASS_WITH_ISSUES", lambda fs: any(f["severity"] == "LOW" for f in fs)),
    ("PASS", lambda fs: True),  # fallthrough
]

EXIT = {"PASS": 0, "PASS_WITH_ISSUES": 1, "NEEDS_WORK": 2, "BLOCKED": 3}


def collect_open(devlyn: pathlib.Path) -> list[dict]:
    open_findings: list[dict] = []
    for jsonl in devlyn.glob("*.findings.jsonl"):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                f = json.loads(line)
            except json.JSONDecodeError:
                # Malformed line surfaces explicitly rather than silently dropping.
                sys.stderr.write(f"warn: malformed finding in {jsonl}: {line[:80]}\n")
                continue
            if f.get("status") == "open":
                open_findings.append(f)
    return open_findings


def compute(findings: list[dict]) -> str:
    for label, pred in PRECEDENCE:
        if pred(findings):
            return label
    return "PASS"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--devlyn-dir", default=".devlyn", help="path to .devlyn/ (default: ./.devlyn)")
    p.add_argument("--json", action="store_true", help="emit JSON summary to stdout")
    args = p.parse_args()

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 3

    findings = collect_open(devlyn)
    verdict = compute(findings)
    by_sev = Counter(f["severity"] for f in findings)

    if args.json:
        json.dump({"verdict": verdict, "open": len(findings), "by_severity": dict(by_sev)}, sys.stdout)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(f"{verdict}\n")
        sys.stdout.write(f"open: {len(findings)} ({' '.join(f'{k}={v}' for k, v in sorted(by_sev.items()))})\n")

    return EXIT[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
