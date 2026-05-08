#!/usr/bin/env python3
"""Headroom gate for candidate L2/pair fixtures.

Pair lift is not measurable when bare and solo already score near the ceiling.
This gate checks the precondition recorded in HANDOFF.md: before an L2 pair
measurement is pre-registered, candidate fixtures must leave enough room for
pair to improve the outcome.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def load_json(path: pathlib.Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def score_for(judge: dict, arm: str) -> int | None:
    scores = judge.get("scores_by_arm") or {}
    value = scores.get(arm)
    return value if isinstance(value, int) else None


def arm_clean_failures(fixture_dir: pathlib.Path, judge: dict, arm: str) -> list[str]:
    failures: list[str] = []
    result = load_json(fixture_dir / arm / "result.json")
    verify = load_json(fixture_dir / arm / "verify.json")
    if result is None:
        failures.append(f"{arm} result.json missing")
    if verify is None:
        failures.append(f"{arm} verify.json missing")
    dq_by_arm = judge.get("disqualifiers_by_arm") or {}
    if bool((dq_by_arm.get(arm) or {}).get("disqualifier")):
        failures.append(f"{arm} judge disqualifier")
    if result is not None:
        if bool(result.get("disqualifier")):
            failures.append(f"{arm} result disqualifier")
        if bool(result.get("timed_out")):
            failures.append(f"{arm} timed out")
        if bool(result.get("invoke_failure")):
            failures.append(f"{arm} invoke failure")
    if verify is not None and bool(verify.get("disqualifier")):
        failures.append(f"{arm} verify disqualifier")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results")
    parser.add_argument("--bare-max", type=int, default=60)
    parser.add_argument("--solo-max", type=int, default=80)
    parser.add_argument("--min-fixtures", type=int, default=2)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)
    args = parser.parse_args()

    res_root = pathlib.Path(args.results_root) / args.run_id
    if not res_root.is_dir():
        print(f"no results dir: {res_root}", file=sys.stderr)
        return 2

    rows = []
    for fixture_dir in sorted(p for p in res_root.iterdir() if p.is_dir()):
        judge = load_json(fixture_dir / "judge.json")
        if judge is None:
            rows.append({
                "fixture": fixture_dir.name,
                "status": "MISSING_JUDGE",
                "reason": "judge.json missing",
            })
            continue
        bare = score_for(judge, "bare")
        solo = score_for(judge, "solo_claude")
        bare_clean_failures = arm_clean_failures(fixture_dir, judge, "bare")
        solo_clean_failures = arm_clean_failures(fixture_dir, judge, "solo_claude")
        bare_ok = bare is not None and bare <= args.bare_max and not bare_clean_failures
        solo_ok = solo is not None and solo <= args.solo_max and not solo_clean_failures
        status = "PASS" if bare_ok and solo_ok else "FAIL"
        reasons = []
        if bare is None:
            reasons.append("bare score missing")
        elif bare > args.bare_max:
            reasons.append(f"bare score {bare} > {args.bare_max}")
        if solo is None:
            reasons.append("solo_claude score missing")
        elif solo > args.solo_max:
            reasons.append(f"solo_claude score {solo} > {args.solo_max}")
        reasons.extend(bare_clean_failures)
        reasons.extend(solo_clean_failures)
        rows.append({
            "fixture": fixture_dir.name,
            "status": status,
            "bare_score": bare,
            "solo_score": solo,
            "reason": "; ".join(reasons) if reasons else "",
        })

    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    fixture_count_ok = len(rows) >= args.min_fixtures
    verdict = "PASS" if pass_count == len(rows) and rows and fixture_count_ok else "FAIL"
    payload = {
        "run_id": args.run_id,
        "rule": f"at least {args.min_fixtures} candidate fixtures; each must satisfy bare <= {args.bare_max} and solo_claude <= {args.solo_max}, with both arms clean",
        "verdict": verdict,
        "fixtures_total": len(rows),
        "fixtures_passed": pass_count,
        "min_fixtures": args.min_fixtures,
        "fixture_count_ok": fixture_count_ok,
        "rows": rows,
    }

    if args.out_json:
        pathlib.Path(args.out_json).write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        f"# Headroom Gate — {args.run_id}",
        "",
        f"Verdict: **{verdict}**",
        "",
        f"Rule: at least {args.min_fixtures} fixtures; bare <= {args.bare_max}, "
        f"solo_claude <= {args.solo_max}, both arms clean.",
        "",
        "| Fixture | Bare | Solo | Status | Reason |",
        "|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['fixture']} | {row.get('bare_score')} | {row.get('solo_score')} | "
            f"{row['status']} | {row.get('reason', '')} |"
        )
    report = "\n".join(lines) + "\n"
    if args.out_md:
        pathlib.Path(args.out_md).write_text(report)
    else:
        print(report)

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
