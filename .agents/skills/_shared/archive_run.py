#!/usr/bin/env python3
"""Archive devlyn:resolve run artifacts per references/pipeline-state.md#archive-contract.

Usage:
    python3 scripts/archive_run.py [--devlyn-dir .devlyn]

Reads run_id from .devlyn/pipeline.state.json, moves per-run artifacts into
.devlyn/runs/<run_id>/, then best-effort prunes to last 10 completed runs
(in-flight runs — phases.final_report.verdict == null — are never deleted).

The contract lives in pipeline-state.md. This script implements it so that
archive behavior is identical across every invocation.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile


PER_RUN_PATTERNS = (
    "pipeline.state.json",
    "*.findings.jsonl",
    "*.log.md",
    "fix-batch.round-*.json",
    "criteria.generated.md",
    "risk-probes.jsonl",
    # iter-0019.8: spec-verify carrier artifacts get archived alongside
    # other per-run state. Killed mid-run cleanup is enforced separately
    # by spec-verify-check.py main() — when source markdown has no json
    # block AND BENCH_WORKDIR is unset (real-user mode), the script drops
    # any pre-existing .devlyn/spec-verify.json so a stale orphan from a
    # killed prior run cannot poison this run's gate.
    "spec-verify.json",
    "spec-verify.results.json",
    "spec-verify-findings.jsonl",
    "verify-merge.summary.json",
    # iter-0033a/2026-04-30 archive-fix iter: NEW /devlyn:resolve emits
    # plan.md (PLAN output) + final-report.md (PHASE 6 render) +
    # cumulative.patch (cumulative diff). Smoke 2's archive listing
    # captured all three; archive_run.py was missing them because the
    # patterns predated the new skill's artifact set. Added explicitly
    # so the move is deterministic.
    "plan.md",
    "final-report.md",
    "cumulative.patch",
    # iter-0033c (Codex R-final-smoke Q2): pair-mode VERIFY emits per-judge
    # deliberation transcripts (verify-judge-claude.md / verify-judge-codex.md
    # — and any future-engine analogue via wildcard). Smoke 1a (F2 l2_forced)
    # surfaced the gap: the orchestrator wrote them and listed them as
    # artifacts, but archive_run.py left them in .devlyn/. Gate 8
    # ("pair_judge findings archive distinguishable") would false-fail on
    # every paired fixture without this glob.
    "verify-judge-*.md",
    "codex-judge.*",
)

SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


def read_run_id(devlyn: pathlib.Path) -> str:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"error: {state_path} is not valid JSON: {e}")
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise SystemExit(f"error: {state_path} has no run_id")
    if not SAFE_RUN_ID_RE.fullmatch(run_id):
        raise SystemExit(f"error: {state_path} run_id must match [A-Za-z0-9_.-]+")
    return run_id


def move_artifacts(devlyn: pathlib.Path, dest: pathlib.Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    moved = 0
    for pat in PER_RUN_PATTERNS:
        for src in devlyn.glob(pat):
            if src.is_file():
                shutil.move(str(src), str(dest / src.name))
                moved += 1
    return moved


def prune(runs_dir: pathlib.Path, keep: int = 10) -> int:
    """Delete oldest completed runs beyond `keep`. In-flight runs never removed."""
    candidates = []
    for d in sorted(runs_dir.glob("*/"), key=lambda p: p.name):
        state_file = d / "pipeline.state.json"
        if not state_file.is_file():
            continue
        try:
            s = loads_strict_json(state_file.read_text(encoding="utf-8"))
        except ValueError:
            # Can't decide flight-state safely; skip (never prune)
            continue
        verdict = s.get("phases", {}).get("final_report", {}).get("verdict")
        if verdict is None:
            continue  # in-flight
        candidates.append(d)
    over = len(candidates) - keep
    if over <= 0:
        return 0
    pruned = 0
    for d in candidates[:over]:  # oldest first (lex sort = chronological)
        shutil.rmtree(d, ignore_errors=False)
        pruned += 1
    return pruned


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp) / ".devlyn"
        devlyn.mkdir()
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "run_id": "run-1",
                "phases": {"final_report": {"verdict": "PASS"}},
            }) + "\n",
            encoding="utf-8",
        )
        for name in (
            "risk-probes.jsonl",
            "verify.pair.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "codex-judge.summary.json",
        ):
            (devlyn / name).write_text("{}\n", encoding="utf-8")
        run_id = read_run_id(devlyn)
        assert run_id == "run-1", run_id
        moved = move_artifacts(devlyn, devlyn / "runs" / run_id)
        assert moved >= 6, moved
        for name in (
            "pipeline.state.json",
            "risk-probes.jsonl",
            "verify.pair.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "codex-judge.summary.json",
        ):
            assert (devlyn / "runs" / run_id / name).is_file(), name

        bad = pathlib.Path(tmp) / "bad"
        bad.mkdir()
        (bad / "pipeline.state.json").write_text('{"run_id": "../escape"}\n', encoding="utf-8")
        try:
            read_run_id(bad)
        except SystemExit as exc:
            assert "run_id must match" in str(exc)
        else:
            raise AssertionError("unsafe archive run_id was accepted")

        nan = pathlib.Path(tmp) / "nan"
        nan.mkdir()
        (nan / "pipeline.state.json").write_text('{"run_id": NaN}\n', encoding="utf-8")
        try:
            read_run_id(nan)
        except SystemExit as exc:
            assert "invalid JSON numeric constant: NaN" in str(exc)
        else:
            raise AssertionError("NaN archive run_id was accepted")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--keep", type=int, default=10, help="keep N most recent completed runs")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1

    run_id = read_run_id(devlyn)
    dest = devlyn / "runs" / run_id
    moved = move_artifacts(devlyn, dest)
    pruned = prune(devlyn / "runs", keep=args.keep)

    sys.stdout.write(f"archived run_id={run_id} files={moved} pruned={pruned}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
