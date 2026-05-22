#!/usr/bin/env python3
"""
Lane B score aggregator — v0 skeleton.

Reads:
  - <run-dir>/manifest.json           (run metadata + A/B slot map)
  - <run-dir>/detector-findings.jsonl (mechanical signals per arm-fixture)
  - <run-dir>/judge-findings.jsonl    (blind judge verdicts per fixture)

Emits:
  - behavior-score.json (7-axis aggregate + summary_verdict)
  - behavior-score.md   (human-readable summary)

Aggregation contract (per RUBRIC.md):
  - For each axis: compare candidate vs baseline wins across fixtures scoring this axis
  - axis_score ∈ {-1, 0, +1}:
      +1 = candidate strictly better (won all fixtures scoring this axis, lost none)
       0 = mixed OR axis not scored by any fixture
      -1 = candidate strictly worse
  - summary_verdict:
      IMPROVED  if ≥3 axes are +1 AND no axis is -1
      REGRESSED if any axis is -1 and IMPROVED does not hold
      MIXED     otherwise

v0 status: scaffold only. Day 2 will wire the actual aggregation once
judge-findings.jsonl has real data. The function shape is set so downstream
consumers can plan around it.
"""
from __future__ import annotations

import argparse
import json
import sys
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
) -> dict:
    """Day 2: actual axis-by-axis tally lives here.

    Today: emit a scaffolded shape so downstream tools see the contract.
    """
    scores = {ax: 0 for ax in AXES}
    if not judge_findings:
        verdict = "PENDING"
        reason = "no judge findings — Day 2 driver not wired yet"
    else:
        # TODO Day 2: tally per-axis winners, apply IMPROVED / REGRESSED / MIXED rule.
        verdict = "SCAFFOLD"
        reason = "aggregation logic pending — see Day 2 TODO in score-behavior.py"

    return {
        "run_id": manifest.get("run_id"),
        "baseline_ref": manifest.get("baseline_ref"),
        "candidate_ref": manifest.get("candidate_ref"),
        "fixtures": manifest.get("fixtures", []),
        "behavior_scores": scores,
        "detector_findings_count": len(detector_findings),
        "judge_findings_count": len(judge_findings),
        "summary_verdict": verdict,
        "summary_reason": reason,
        "schema_version": "v0",
    }


def render_md(score: dict) -> str:
    lines = [
        f"# Behavior score — {score['run_id']}",
        "",
        f"- baseline: `{score['baseline_ref']}`",
        f"- candidate: `{score['candidate_ref']}`",
        f"- fixtures: {len(score['fixtures'])}",
        f"- detector findings: {score['detector_findings_count']}",
        f"- judge findings: {score['judge_findings_count']}",
        f"- **verdict**: `{score['summary_verdict']}` — {score['summary_reason']}",
        "",
        "## Behavior axes",
        "",
        "| axis | score |",
        "|---|---|",
    ]
    for axis, value in score["behavior_scores"].items():
        lines.append(f"| `{axis}` | {value:+d} |")
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

    score = aggregate(manifest, detector_findings, judge_findings)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(score), encoding="utf-8")

    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    print(f"verdict: {score['summary_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
