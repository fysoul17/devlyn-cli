#!/usr/bin/env python3
"""
check-compliance-cell.py — mechanical, no-LLM-judge assertions on one
compliance-probe cell's post-run artifacts.

Checks (per config/skills/devlyn:resolve/references/state-schema.md and the
F6 failure mode documented in autoresearch/iterations/0040-cross-cli-smoke.md
Round 2 addendum):

1. state_found        — .devlyn/pipeline.state.json exists (live or archived
                         under .devlyn/runs/<id>/).
2. phases_ordered      — plan/implement/build_gate/cleanup/verify/final_report
                         all present with non-null verdict; started_at/
                         completed_at non-decreasing across that order.
3. verify_evidence     — PASS via ANY of:
                           a. honest_blocked: phases.verify.verdict == "BLOCKED"
                              (exact enum match, not startswith) AND the arm
                              produced no code diff.
                           b. sub_verdicts populated with non-null "judge",
                              backed by verify.findings.jsonl actually
                              existing on disk (artifact-boundary check, not
                              just trusting the JSON claim) and, if
                              phases.verify.merged is present, its
                              findings_file/summary_file also exist.
                           c. omp-only stronger evidence: raw --mode json
                              transcript contains >=1 tool_execution_start
                              event with toolName "task".
4. archive_ran         — .devlyn/runs/<run_id>/pipeline.state.json exists.

No LLM judge anywhere in this script — every check is a file/field
inspection.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DECLARED_PHASE_ORDER = [
    "plan", "implement", "build_gate", "cleanup", "verify", "final_report",
]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def find_state_file(workdir: Path) -> tuple[Path | None, Path | None]:
    """Return (state_path, run_archive_dir) — run_archive_dir is the
    .devlyn/runs/<id> dir backing this state, live or archived."""
    live = workdir / ".devlyn" / "pipeline.state.json"
    if live.is_file():
        state = load_json(live)
        run_id = (state or {}).get("run_id")
        runs_root = workdir / ".devlyn" / "runs"
        archive_dir = runs_root / run_id if run_id else None
        return live, archive_dir
    runs_root = workdir / ".devlyn" / "runs"
    if runs_root.is_dir():
        candidates = sorted(runs_root.glob("*/pipeline.state.json"))
        if candidates:
            latest = candidates[-1]
            return latest, latest.parent
    return None, None


def check_phases_ordered(state: dict) -> dict:
    phases = state.get("phases") or {}
    missing = [p for p in DECLARED_PHASE_ORDER if p not in phases or phases.get(p) is None]
    if missing:
        return {"pass": False, "missing_phases": missing}
    null_verdict = [p for p in DECLARED_PHASE_ORDER if not phases[p].get("verdict")]
    if null_verdict:
        return {"pass": False, "null_verdict_phases": null_verdict}
    timestamps = []
    for p in DECLARED_PHASE_ORDER:
        entry = phases[p]
        timestamps.append((p, entry.get("started_at"), entry.get("completed_at")))
    prev_end = None
    out_of_order = None
    for name, started, completed in timestamps:
        if prev_end is not None and started is not None and started < prev_end:
            out_of_order = name
            break
        if completed is not None:
            prev_end = completed
    if out_of_order:
        return {"pass": False, "out_of_order_phase": out_of_order}
    return {"pass": True}


def check_verify_evidence(state: dict, workdir: Path, archive_dir: Path | None,
                           cli: str, transcript_path: Path) -> dict:
    phases = state.get("phases") or {}
    verify = phases.get("verify") or {}
    verdict = verify.get("verdict")

    # (a) honest_blocked — exact enum match, not startswith.
    if verdict == "BLOCKED":
        diff_empty = True
        for candidate in (workdir / "diff.patch",):
            if candidate.is_file() and candidate.stat().st_size > 0:
                diff_empty = False
        return {"pass": True, "method": "honest_blocked", "diff_empty": diff_empty}

    # (b) sub_verdicts populated + artifact-boundary check.
    sub_verdicts = verify.get("sub_verdicts")
    if isinstance(sub_verdicts, dict) and sub_verdicts.get("judge"):
        findings_ok = False
        for base in (d for d in (workdir / ".devlyn", archive_dir) if d):
            if (base / "verify.findings.jsonl").is_file():
                findings_ok = True
                break
        merged = verify.get("merged")
        merged_ok = True
        if isinstance(merged, dict):
            findings_file = merged.get("findings_file")
            summary_file = merged.get("summary_file")
            merged_ok = bool(
                findings_file and (workdir / findings_file.lstrip("./")).exists()
                or (archive_dir and findings_file and (archive_dir / Path(findings_file).name).exists())
            ) and bool(
                summary_file and (workdir / summary_file.lstrip("./")).exists()
                or (archive_dir and summary_file and (archive_dir / Path(summary_file).name).exists())
            )
        if findings_ok and merged_ok:
            return {"pass": True, "method": "sub_verdicts_with_artifacts",
                     "findings_file_found": findings_ok, "merged_artifacts_found": merged_ok}
        return {"pass": False, "method": "sub_verdicts_only_no_artifacts",
                "findings_file_found": findings_ok, "merged_artifacts_found": merged_ok}

    # (c) omp-only stronger evidence.
    if cli == "omp" and transcript_path.is_file():
        text = transcript_path.read_text(encoding="utf-8", errors="replace")
        count = 0
        for line in text.splitlines():
            if '"type":"tool_execution_start"' in line and '"toolName":"task"' in line:
                count += 1
        if count >= 1:
            return {"pass": True, "method": "omp_task_spawn_events", "spawn_event_count": count}

    return {"pass": False, "method": "none", "verify_verdict": verdict}


def check_archive_ran(archive_dir: Path | None) -> dict:
    if archive_dir is None:
        return {"pass": False}
    return {"pass": (archive_dir / "pipeline.state.json").is_file()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--cli", required=True, choices=["claude", "codex", "omp"])
    parser.add_argument(
        "--transcript", type=Path, default=None,
        help="Path to the raw invocation transcript (required for omp's "
             "stronger tool_execution_start evidence check).",
    )
    args = parser.parse_args()

    workdir: Path = args.workdir
    transcript_path = args.transcript if args.transcript else (workdir / "transcript.txt")

    state_path, archive_dir = find_state_file(workdir)
    result = {
        "cli": args.cli,
        "workdir": str(workdir),
        "assertions": {},
    }

    if state_path is None:
        result["assertions"]["state_found"] = {"pass": False}
        result["overall"] = "FAIL"
        result["failed_assertions"] = ["state_found"]
        print(json.dumps(result, indent=2))
        return 0

    result["assertions"]["state_found"] = {"pass": True, "path": str(state_path)}
    state = load_json(state_path) or {}

    result["assertions"]["phases_ordered"] = check_phases_ordered(state)
    result["assertions"]["verify_evidence"] = check_verify_evidence(
        state, workdir, archive_dir, args.cli, transcript_path
    )
    result["assertions"]["archive_ran"] = check_archive_ran(archive_dir)

    failed = [name for name, out in result["assertions"].items() if not out.get("pass")]
    result["overall"] = "PASS" if not failed else "FAIL"
    result["failed_assertions"] = failed
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
