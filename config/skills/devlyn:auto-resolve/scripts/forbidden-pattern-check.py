#!/usr/bin/env python3
"""Forbidden-pattern verification gate (iter-0028).

Companion to spec-verify-check.py. Runs at BUILD_GATE phase BEFORE EVAL,
so a silent-catch / @ts-ignore / eslint-disable / etc. introduced by this
build is caught by the fix-loop instead of slipping through to EVAL where
it becomes a DQ at scoring time.

Why this exists (iter-0027 → iter-0028 lesson): F2 N=5 paired variance
showed L1 silent-catch DQ rate 2/5 (40%) at the same git baseline,
same engine, same prompt. The runtime principle prose at
phase-1-build.md:61-67 says "no silent catch" but empirically does not
prevent it — same pattern as iter-0008 prompt-only engine constraint
dead-end and iter-0019.6 prompt-only spec-verify dead-end. Mechanical
BUILD_GATE enforcement makes the violation visible to BUILD via the fix-
loop (with a CRITICAL finding the fix-round must clear) instead of only
to the post-run judge.

Source-of-truth resolution (iter-0028 R0 verdict — Codex 2026-04-30):
- Bench mode (BENCH_WORKDIR set): run-fixture.sh stages
  `.devlyn/forbidden-patterns.json` from `expected.json:forbidden_patterns`
  alongside `.devlyn/spec-verify.json`. Same staging contract; the script
  itself stays benchmark-agnostic and never reads expected.json directly.
- Real-user mode (no BENCH_WORKDIR): no carrier file, silent no-op. A
  real-user default policy file is deferred (iter-0028 R0 falsification F2:
  "real-user default policy is overreach for this iter; no acceptance
  measurement"). Future iter may add it with drift parity + false-positive
  acceptance.

Severity preservation (iter-0028 R0 critical tweak): only patterns with
severity=="disqualifier" emit a CRITICAL/blocking finding. Patterns with
severity=="warning" (e.g. F6's `npm install --no-save` advisory) are
recorded in the results file but DO NOT become CRITICAL — that would
regress fixtures that currently pass with warning-severity hits. The
post-run scanner in run-fixture.sh:563-565 already disqualifies only on
`disqualifier`-severity hits; this script mirrors that semantics.

Diff-scope semantics: scan the unified diff (HEAD..workdir), not whole
files. Mirrors the post-run scanner's `slice_diff_to_files` semantics
(run-fixture.sh:493-523) so we only flag patterns introduced by THIS
build, never pre-existing patterns in untouched code.

Exit codes:
- 0: no carrier file (silent no-op for real-user) OR no disqualifier-
  severity hits (warning hits OK).
- 1: at least one disqualifier-severity hit; CRITICAL finding(s) written
  to `.devlyn/forbidden-pattern-findings.jsonl`. BUILD_GATE merges this
  onto `build_gate.findings.jsonl` and the orchestrator routes FAIL
  → fix-loop reruns BUILD.
- 2: invocation error (unreadable / malformed carrier).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


SILENT_CATCH_HINT = re.compile(
    r"silent[-_ ]?catch|empty[-_ ]?catch|swallow(?:ed|s|ing)?[-_ ]?(?:catch|error|exception)",
    re.IGNORECASE,
)


def slice_diff_to_files(diff: str, files: list[str]) -> str:
    """Return the subset of a unified diff touching any of `files`. Hunks
    outside the allowlist are dropped. Mirrors run-fixture.sh:502-513."""
    if not files:
        return diff
    out: list[str] = []
    keep = False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            keep = any(f in line for f in files)
        if keep:
            out.append(line)
    return "".join(out)


def get_diff(work: Path) -> str:
    """Compute unified diff of the BUILD's full output vs the pre-BUILD
    baseline. iter-0028 R1 D1 fix: `git diff HEAD` was wrong — auto-resolve
    PHASE 1 ends with `git add -A && git commit -m "...build complete"`
    (SKILL.md:113-117), so by BUILD_GATE time HEAD already includes BUILD's
    changes and `git diff HEAD` returns empty, silently disabling the
    scanner.

    Resolution order:
      1. `DEVLYN_DIFF_BASE_SHA` env var — set by run-fixture.sh to
         `SCAFFOLD_SHA` (benchmark) or by auto-resolve to the pre-BUILD
         commit SHA (real-user; contract addition for iter-0028).
      2. Fallback to `HEAD` — preserves smoke-test ergonomics and the
         pre-BUILD-commit case (e.g. dry-run before BUILD has committed).

    Returns "" if git is unavailable or the base ref is missing — silent
    fall-through (treated as "no diff to scan", exit 0). This matches
    run-fixture.sh's behavior of just-failing-to-find-patterns rather than
    blocking the build on environmental issues."""
    base = os.environ.get("DEVLYN_DIFF_BASE_SHA") or "HEAD"
    try:
        proc = subprocess.run(
            ["git", "diff", base],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return ""
        return proc.stdout or ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def validate_shape(carrier: object) -> str | None:
    """Return None if the carrier matches the expected shape; otherwise
    a human-readable error string."""
    if not isinstance(carrier, dict):
        return "carrier must be a JSON object"
    patterns = carrier.get("forbidden_patterns")
    if patterns is None:
        return "carrier missing 'forbidden_patterns' key"
    if not isinstance(patterns, list):
        return "'forbidden_patterns' must be a list"
    for i, fp in enumerate(patterns):
        if not isinstance(fp, dict):
            return f"forbidden_patterns[{i}] must be a JSON object"
        if not isinstance(fp.get("pattern"), str) or not fp["pattern"]:
            return f"forbidden_patterns[{i}].pattern must be a non-empty string"
        try:
            re.compile(fp["pattern"])
        except re.error as e:
            return f"forbidden_patterns[{i}].pattern invalid regex: {e}"
        files = fp.get("files")
        if files is not None and not isinstance(files, list):
            return f"forbidden_patterns[{i}].files must be a list or omitted"
    return None


def classify_rule_id(fp: dict) -> str:
    """Pick a finding rule_id by inspecting the pattern's description. Keeps
    silent-catch as its own rule_id so iter-0028 acceptance measurement
    can filter for it.

    iter-0028 R1 D2 fix: classification is description-only (was
    `description + ("catch" in pattern)` which would mislabel non-silent
    catch-mentioning patterns in future fixtures). The pattern regex itself
    is not authoritative for naming — the fixture's `description` is."""
    desc = fp.get("description") or ""
    if SILENT_CATCH_HINT.search(desc):
        return "correctness.silent-catch-introduced"
    return "correctness.forbidden-pattern-introduced"


def main() -> int:
    bench_mode = "BENCH_WORKDIR" in os.environ
    work = Path(os.environ.get("BENCH_WORKDIR") or os.getcwd())
    devlyn_dir = work / ".devlyn"
    carrier_path = devlyn_dir / "forbidden-patterns.json"
    results_path = devlyn_dir / "forbidden-pattern.results.json"
    findings_path = devlyn_dir / "forbidden-pattern-findings.jsonl"

    if not carrier_path.exists():
        # Real-user mode default OR bench fixture without forbidden_patterns
        # — silent no-op. Drop any stale findings file from a prior round
        # so the BUILD_GATE merge step does not pick up dead findings.
        if findings_path.exists():
            findings_path.unlink()
        return 0

    try:
        carrier = json.loads(carrier_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[forbidden-pattern] error: cannot parse {carrier_path}: {e}",
              file=sys.stderr)
        return 2

    shape_err = validate_shape(carrier)
    if shape_err:
        print(f"[forbidden-pattern] error: {carrier_path}: {shape_err}",
              file=sys.stderr)
        return 2

    patterns = carrier["forbidden_patterns"]
    if not patterns:
        if findings_path.exists():
            findings_path.unlink()
        return 0

    diff_text = get_diff(work)

    hits: list[dict] = []
    findings: list[dict] = []
    finding_seq = 1

    for fp in patterns:
        scope = slice_diff_to_files(diff_text, fp.get("files") or [])
        if not scope:
            continue
        match = re.search(fp["pattern"], scope)
        if not match:
            continue

        severity = fp.get("severity", "warning")
        hit = {
            "pattern": fp["pattern"],
            "severity": severity,
            "description": fp.get("description", ""),
            "scoped_to": fp.get("files") or "all",
            "match_excerpt": match.group(0)[:200],
        }
        hits.append(hit)

        if severity != "disqualifier":
            # Warnings are reported but NOT blocking — preserves F6 behavior
            # (Codex R0 F5 falsification). Post-run scanner still records
            # them for the judge.
            continue

        rule_id = classify_rule_id(fp)
        scoped = fp.get("files") or "all changed files"
        scoped_str = ", ".join(scoped) if isinstance(scoped, list) else scoped
        msg = (
            f"Forbidden pattern (severity=disqualifier) introduced in this "
            f"build: {fp.get('description') or fp['pattern']}. Match: "
            f"{match.group(0)[:200]!r}. Scoped to: {scoped_str}."
        )
        fix_hint = (
            f"Remove the disqualifier-severity match from the diff. The "
            f"runtime contract (`_shared/runtime-principles.md` no-workaround "
            f"section) forbids silent catches, `@ts-ignore`, and similar "
            f"escape hatches; replace the construct with explicit error "
            f"handling that surfaces the failure (logged + propagated) per "
            f"the project's error-handling philosophy. See "
            f"`.devlyn/forbidden-pattern.results.json` for the captured "
            f"match excerpt."
        )

        findings.append({
            "id": f"BGATE-FP-{finding_seq:04d}",
            "rule_id": rule_id,
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": msg,
            "file": ".devlyn/forbidden-patterns.json",
            "line": 1,
            "phase": "build_gate",
            "criterion_ref": f"forbidden-pattern://{fp['pattern']}",
            "fix_hint": fix_hint,
            "blocking": True,
            "status": "open",
        })
        finding_seq += 1

    devlyn_dir.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps({"hits": hits}, indent=2) + "\n")

    # Per-round artifact: truncate each run so a prior fix-round's findings
    # do not stick after the violation is removed.
    with findings_path.open("w") as fh:
        for f in findings:
            fh.write(json.dumps(f) + "\n")

    if findings:
        print(
            f"[forbidden-pattern] {len(findings)} disqualifier-severity "
            f"hit(s); CRITICAL finding(s) written to {findings_path}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
