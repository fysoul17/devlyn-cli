#!/usr/bin/env python3
"""Gate frozen VERIFY solo-vs-pair evidence.

This gate is intentionally narrower than headroom-gate.py. It does not claim
full-pipeline pair superiority. It verifies the leak-free thing we can measure:
given a fixed external diff, gated pair VERIFY fires and contributes a stricter
verdict-binding result. That can be either stricter than the separate solo arm
or stricter than the pair run's own primary judge, which avoids stochastic
solo-vs-pair confounding. Passing evidence must come from distinct fixture ids
with runner input metadata present.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


VERDICT_RANK = {
    "PASS": 0,
    "PASS_WITH_ISSUES": 1,
    "NEEDS_WORK": 2,
    "BLOCKED": 3,
}


def load_compare(results_root: Path, run_id: str) -> dict[str, Any]:
    compare_path = results_root / run_id / "compare.json"
    if not compare_path.exists():
        raise FileNotFoundError(f"missing compare.json for {run_id}: {compare_path}")
    with compare_path.open() as f:
        return json.load(f)


def rank(verdict: str | None) -> int:
    return VERDICT_RANK.get(verdict or "", -1)


def elapsed_ratio(pair_elapsed: Any, solo_elapsed: Any) -> float | None:
    if not isinstance(pair_elapsed, (int, float)) or not isinstance(solo_elapsed, (int, float)):
        return None
    if solo_elapsed <= 0:
        return None
    return pair_elapsed / solo_elapsed


def infer_fixture_id(results_root: Path, run_id: str) -> str | None:
    run_root = results_root / run_id
    for arm in ("pair", "solo"):
        input_path = run_root / arm / "input.md"
        if not input_path.exists():
            continue
        match = re.search(r"docs/roadmap/phase-1/([^`\s]+)\.md", input_path.read_text())
        if match:
            return match.group(1)
    return None


def transcript_failure_reason(results_root: Path, run_id: str, arm: str) -> str | None:
    transcript_path = results_root / run_id / arm / "transcript.txt"
    if not transcript_path.is_file():
        return None
    transcript = transcript_path.read_text(encoding="utf8", errors="replace")
    if "You've hit your limit" in transcript:
        return "provider_limit"
    return None


def evaluate_run(
    results_root: Path,
    fixtures_root: Path,
    run_id: str,
    max_pair_solo_wall_ratio: float | None,
) -> dict[str, Any]:
    try:
        compare = load_compare(results_root, run_id)
    except FileNotFoundError as exc:
        fixture_id = infer_fixture_id(results_root, run_id)
        return {
            "run_id": run_id,
            "fixture_id": fixture_id,
            "status": "FAIL",
            "failures": [str(exc)],
            "solo_verdict": None,
            "pair_verdict": None,
            "pair_mode": False,
            "pair_trigger_missed": False,
            "pair_verdict_lift": False,
            "pair_internal_verdict_lift": False,
            "pair_primary_verdict": None,
            "pair_judge_verdict": None,
            "solo_elapsed_seconds": None,
            "pair_elapsed_seconds": None,
            "pair_solo_wall_ratio": None,
            "pair_severity_counts": {},
        }
    solo = compare.get("solo") or {}
    pair = compare.get("pair") or {}
    comparison = compare.get("comparison") or {}
    solo_failure_reason = solo.get("invoke_failure_reason") or transcript_failure_reason(
        results_root, run_id, "solo"
    )
    pair_failure_reason = pair.get("invoke_failure_reason") or transcript_failure_reason(
        results_root, run_id, "pair"
    )

    failures: list[str] = []
    if solo.get("timed_out"):
        failures.append("solo timed out")
    if pair.get("timed_out"):
        failures.append("pair timed out")
    if solo_failure_reason == "provider_limit":
        failures.append("solo provider limit")
    if pair_failure_reason == "provider_limit":
        failures.append("pair provider limit")
    if solo.get("invoke_exit") != 0:
        failures.append(f"solo invoke_exit={solo.get('invoke_exit')}")
    if pair.get("invoke_exit") != 0:
        failures.append(f"pair invoke_exit={pair.get('invoke_exit')}")
    if not pair.get("pair_mode"):
        failures.append("pair_mode false")
    if comparison.get("pair_trigger_missed"):
        failures.append("pair trigger missed")
    external_lift = bool(comparison.get("pair_verdict_lift"))
    internal_lift = bool(comparison.get("pair_internal_verdict_lift"))
    if not (external_lift or internal_lift):
        failures.append("pair verdict lift false")

    solo_verdict = (
        comparison.get("solo_verdict")
        or solo.get("verify_verdict")
        or solo.get("terminal_verdict")
    )
    pair_verdict = (
        comparison.get("pair_verdict")
        or pair.get("verify_verdict")
        or pair.get("terminal_verdict")
    )
    pair_primary_verdict = comparison.get("pair_primary_verdict")
    pair_judge_verdict = comparison.get("pair_judge_verdict")
    if external_lift and rank(pair_verdict) <= rank(solo_verdict):
        failures.append(f"pair verdict {pair_verdict} not stricter than solo {solo_verdict}")
    if internal_lift and rank(pair_judge_verdict) <= rank(pair_primary_verdict):
        failures.append(
            f"pair_judge verdict {pair_judge_verdict} not stricter than primary {pair_primary_verdict}"
        )
    if rank(pair_verdict) < VERDICT_RANK["NEEDS_WORK"]:
        failures.append(f"pair verdict {pair_verdict} is not verdict-binding")
    pair_elapsed = pair.get("elapsed_seconds")
    solo_elapsed = solo.get("elapsed_seconds")
    wall_ratio = elapsed_ratio(pair_elapsed, solo_elapsed)
    if max_pair_solo_wall_ratio is not None:
        if wall_ratio is None:
            failures.append("pair/solo wall ratio missing")
        elif wall_ratio > max_pair_solo_wall_ratio:
            failures.append(
                f"pair/solo wall ratio {wall_ratio:.2f} exceeds {max_pair_solo_wall_ratio:.2f}"
            )
    fixture_id = infer_fixture_id(results_root, run_id)
    if not fixture_id:
        failures.append("fixture_id missing")
    elif not (fixtures_root / fixture_id).is_dir():
        failures.append(f"fixture_id not found: {fixture_id}")

    return {
        "run_id": run_id,
        "fixture_id": fixture_id,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "solo_verdict": solo_verdict,
        "pair_verdict": pair_verdict,
        "pair_mode": bool(pair.get("pair_mode")),
        "pair_trigger_missed": bool(comparison.get("pair_trigger_missed")),
        "pair_verdict_lift": external_lift,
        "pair_internal_verdict_lift": internal_lift,
        "pair_primary_verdict": pair_primary_verdict,
        "pair_judge_verdict": pair_judge_verdict,
        "solo_elapsed_seconds": solo_elapsed,
        "pair_elapsed_seconds": pair_elapsed,
        "pair_solo_wall_ratio": wall_ratio,
        "solo_failure_reason": solo_failure_reason,
        "pair_failure_reason": pair_failure_reason,
        "pair_severity_counts": pair.get("severity_counts") or {},
    }


def format_ratio(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}x"
    return "n/a"


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Frozen VERIFY Gate — {report['run_ids_label']}",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        "Rule: every supplied run must be clean, each run must cover a distinct fixture, "
        "gated pair VERIFY must fire, and pair must contribute a stricter "
        "verdict-binding result than either the separate solo arm or the pair "
        "run's own primary judge.",
        "",
        f"Minimum passing runs: {report['min_runs']}",
        f"Max pair/solo wall ratio: {format_ratio(report.get('max_pair_solo_wall_ratio'))}",
        f"Average pair/solo wall ratio: {format_ratio(report.get('avg_pair_solo_wall_ratio'))}",
        "",
        "| Run | Fixture | Solo | Pair | Pair mode | Wall ratio | External lift | Internal lift | Status | Reason |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        reason = "; ".join(row["failures"]) if row["failures"] else "ok"
        lines.append(
            f"| {row['run_id']} | {row.get('fixture_id') or 'unknown'} | "
            f"{row['solo_verdict']} | {row['pair_verdict']} | "
            f"{str(row['pair_mode']).lower()} | {format_ratio(row.get('pair_solo_wall_ratio'))} | "
            f"{str(row['pair_verdict_lift']).lower()} | "
            f"{str(row['pair_internal_verdict_lift']).lower()} | "
            f"{row['status']} | {reason} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results")
    parser.add_argument("--fixtures-root", default="benchmark/auto-resolve/fixtures")
    parser.add_argument("--run-id", action="append", required=True)
    parser.add_argument("--min-runs", type=int, default=2)
    parser.add_argument(
        "--max-pair-solo-wall-ratio",
        type=float,
        help="Optional efficiency cap. When set, every run must include elapsed_seconds and pair/solo wall ratio must not exceed this value.",
    )
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    args = parser.parse_args()

    results_root = Path(args.results_root)
    fixtures_root = Path(args.fixtures_root)
    rows = [
        evaluate_run(results_root, fixtures_root, run_id, args.max_pair_solo_wall_ratio)
        for run_id in args.run_id
    ]
    fixture_counts: dict[str, int] = {}
    for row in rows:
        fixture_id = row.get("fixture_id")
        if fixture_id:
            fixture_counts[fixture_id] = fixture_counts.get(fixture_id, 0) + 1
    for row in rows:
        fixture_id = row.get("fixture_id")
        if fixture_id and fixture_counts.get(fixture_id, 0) > 1:
            row["failures"].append(f"duplicate fixture_id={fixture_id}")
            row["status"] = "FAIL"
    passing = [row for row in rows if row["status"] == "PASS"]
    verdict = "PASS" if len(passing) >= args.min_runs and len(passing) == len(rows) else "FAIL"
    ratios = [
        row["pair_solo_wall_ratio"]
        for row in rows
        if isinstance(row.get("pair_solo_wall_ratio"), (int, float))
    ]

    report = {
        "run_ids_label": ", ".join(args.run_id),
        "rule": "clean frozen diff; distinct fixture per run; gated pair VERIFY fires; pair contributes a stricter verdict-binding result; optional pair/solo wall-ratio cap",
        "min_runs": args.min_runs,
        "max_pair_solo_wall_ratio": args.max_pair_solo_wall_ratio,
        "avg_pair_solo_wall_ratio": (sum(ratios) / len(ratios)) if ratios else None,
        "verdict": verdict,
        "runs_total": len(rows),
        "runs_passed": len(passing),
        "rows": rows,
    }

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    if args.out_md:
        write_markdown(Path(args.out_md), report)

    print(json.dumps(report, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
