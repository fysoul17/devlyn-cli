#!/usr/bin/env python3
"""Archive auto-resolve run artifacts per references/pipeline-state.md#archive-contract.

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
import shutil
import sys


PER_RUN_PATTERNS = (
    "pipeline.state.json",
    "*.findings.jsonl",
    "*.log.md",
    "fix-batch.round-*.json",
    "criteria.generated.md",
    # iter-0019.8: spec-verify carrier artifacts get archived alongside
    # other per-run state. Killed mid-run cleanup is enforced separately
    # by spec-verify-check.py main() — when source markdown has no json
    # block AND BENCH_WORKDIR is unset (real-user mode), the script drops
    # any pre-existing .devlyn/spec-verify.json so a stale orphan from a
    # killed prior run cannot poison this run's gate.
    "spec-verify.json",
    "spec-verify.results.json",
    "spec-verify-findings.jsonl",
)


def read_run_id(devlyn: pathlib.Path) -> str:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"error: {state_path} is not valid JSON: {e}")
    run_id = state.get("run_id")
    if not run_id:
        raise SystemExit(f"error: {state_path} has no run_id")
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
            s = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--keep", type=int, default=10, help="keep N most recent completed runs")
    args = ap.parse_args()

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
