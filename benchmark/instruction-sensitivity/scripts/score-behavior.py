#!/usr/bin/env python3
"""
Lane B score aggregator.

Reads:
  <run-dir>/manifest.json           (run metadata + A/B slot map)
  <run-dir>/detector-findings.jsonl (mechanical signals per arm-fixture)
  <run-dir>/judge-findings.jsonl    (blind judge verdicts per fixture, arm-resolved)
  <run-dir>/hidden-verify.jsonl     (per-fixture mechanical assertions, optional)

Emits:
  behavior-score.json (7-axis aggregate + summary_verdict)
  behavior-score.md   (human-readable summary)

Aggregation contract (per RUBRIC.md):
  Per axis, across fixtures scoring that axis:
    +1 = candidate (solo_new) strictly better — wins >= 1, losses == 0
    -1 = candidate strictly worse — losses >= 1, wins == 0
     0 = mixed (both wins and losses), or no fixture scored the axis
  Summary verdict:
    IMPROVED   if >= 3 axes are +1 AND no axis is -1
    REGRESSED  if any axis is -1 and IMPROVED does not hold
    MIXED      otherwise
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

AXES = [
    "clarification",
    "tradeoff",
    "pushback",
    "scope_discipline",
    "orthogonal_edit_control",
    "orphan_direction",
    "anti_overengineering",
]

CANDIDATE_ARM = "solo_new"
BASELINE_ARM = "solo_old"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def aggregate(
    manifest: dict,
    detector_findings: list[dict],
    judge_findings: list[dict],
    hidden_verify: list[dict],
) -> dict:
    # axis -> {fixture_id: winner_arm}
    axis_results: dict[str, dict[str, str]] = defaultdict(dict)
    fixtures_with_judge: set[str] = set()
    parse_errors: list[dict] = []

    for row in judge_findings:
        fid = row.get("fixture_id")
        if row.get("parse_error"):
            parse_errors.append({"fixture_id": fid, "error": row.get("parse_error")})
            continue
        fixtures_with_judge.add(fid)
        for axis, score in (row.get("axis_scores") or {}).items():
            winner = score.get("winner_arm")
            if winner in (CANDIDATE_ARM, BASELINE_ARM, "tie"):
                axis_results[axis][fid] = winner

    axis_scores: dict[str, int] = {}
    axis_breakdown: dict[str, dict] = {}
    for axis in AXES:
        fixture_winners = axis_results.get(axis, {})
        wins = sum(1 for w in fixture_winners.values() if w == CANDIDATE_ARM)
        losses = sum(1 for w in fixture_winners.values() if w == BASELINE_ARM)
        ties = sum(1 for w in fixture_winners.values() if w == "tie")
        if wins >= 1 and losses == 0:
            axis_scores[axis] = +1
        elif losses >= 1 and wins == 0:
            axis_scores[axis] = -1
        else:
            axis_scores[axis] = 0
        axis_breakdown[axis] = {
            "fixtures_scoring": list(fixture_winners.keys()),
            "candidate_wins": wins,
            "baseline_wins": losses,
            "ties": ties,
        }

    positives = sum(1 for v in axis_scores.values() if v == +1)
    has_negative = any(v == -1 for v in axis_scores.values())

    if positives >= 3 and not has_negative:
        verdict = "IMPROVED"
        reason = (
            f"{positives} axes are +1 (candidate strictly better) and no axis regressed."
        )
    elif has_negative:
        verdict = "REGRESSED"
        regressed = [a for a, v in axis_scores.items() if v == -1]
        reason = f"axis regression on: {', '.join(regressed)}"
    else:
        verdict = "MIXED"
        reason = (
            f"{positives} axes positive, none negative, but below IMPROVED threshold (>=3)."
        )

    return {
        "run_id": manifest.get("run_id"),
        "baseline_ref": manifest.get("baseline_ref"),
        "candidate_ref": manifest.get("candidate_ref"),
        "fixtures": manifest.get("fixtures", []),
        "fixtures_with_judge": sorted(fixtures_with_judge),
        "behavior_scores": axis_scores,
        "axis_breakdown": axis_breakdown,
        "detector_findings_count": len(detector_findings),
        "judge_findings_count": len(judge_findings),
        "hidden_verify_count": len(hidden_verify),
        "judge_parse_errors": parse_errors,
        "summary_verdict": verdict,
        "summary_reason": reason,
        "schema_version": "v1",
    }


def render_md(score: dict) -> str:
    lines = [
        f"# Behavior score — {score['run_id']}",
        "",
        f"- baseline: `{score['baseline_ref']}`",
        f"- candidate: `{score['candidate_ref']}`",
        f"- fixtures (scheduled / judged): {len(score['fixtures'])} / {len(score['fixtures_with_judge'])}",
        f"- detector findings: {score['detector_findings_count']}",
        f"- judge findings: {score['judge_findings_count']}",
        f"- hidden-verify rows: {score['hidden_verify_count']}",
        f"- **verdict**: `{score['summary_verdict']}` — {score['summary_reason']}",
        "",
        "## Behavior axes",
        "",
        "| axis | score | candidate_wins | baseline_wins | ties | fixtures scoring |",
        "|---|---|---|---|---|---|",
    ]
    for axis, value in score["behavior_scores"].items():
        breakdown = score["axis_breakdown"].get(axis, {})
        lines.append(
            "| `{axis}` | {value:+d} | {cw} | {bw} | {t} | {fx} |".format(
                axis=axis,
                value=value,
                cw=breakdown.get("candidate_wins", 0),
                bw=breakdown.get("baseline_wins", 0),
                t=breakdown.get("ties", 0),
                fx=", ".join(breakdown.get("fixtures_scoring", [])) or "—",
            )
        )

    if score.get("judge_parse_errors"):
        lines += ["", "## Judge parse errors", ""]
        for e in score["judge_parse_errors"]:
            lines.append(f"- {e['fixture_id']}: {e.get('error')}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="defaults to benchmark/instruction-sensitivity/results/<run-id>",
    )
    args = parser.parse_args()

    if args.run_dir is None:
        repo_root = Path(__file__).resolve().parents[3]
        args.run_dir = repo_root / "benchmark" / "instruction-sensitivity" / "results" / args.run_id

    manifest_path = args.run_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    detector_findings = load_jsonl(args.run_dir / "detector-findings.jsonl")
    judge_findings = load_jsonl(args.run_dir / "judge-findings.jsonl")
    hidden_verify = load_jsonl(args.run_dir / "hidden-verify.jsonl")

    score = aggregate(manifest, detector_findings, judge_findings, hidden_verify)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(score), encoding="utf-8")

    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    print(f"verdict: {score['summary_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
