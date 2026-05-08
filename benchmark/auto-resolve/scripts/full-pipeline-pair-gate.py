#!/usr/bin/env python3
"""Gate full-pipeline L2/pair evidence against L1 solo.

This is stricter than headroom-gate.py. Headroom only says a candidate set is
worth measuring. This gate says the measured L2 arm is usable evidence:
bare and solo leave headroom, l2_gated is clean, gated pair actually fired, and
the blind judge scores l2_gated materially above solo_claude.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


def load_json(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def score_for(judge: dict[str, Any], arm: str) -> int | None:
    value = (judge.get("scores_by_arm") or {}).get(arm)
    return value if isinstance(value, int) else None


def clean_failures(fixture_dir: pathlib.Path, judge: dict[str, Any], arm: str) -> list[str]:
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
            reason = result.get("invoke_failure_reason")
            if isinstance(reason, str) and reason:
                failures.append(f"{arm} invoke failure ({reason})")
            else:
                failures.append(f"{arm} invoke failure")
    if verify is not None and bool(verify.get("disqualifier")):
        failures.append(f"{arm} verify disqualifier")
    return failures


def elapsed_ratio(pair_result: dict[str, Any] | None, solo_result: dict[str, Any] | None) -> float | None:
    if pair_result is None or solo_result is None:
        return None
    pair_elapsed = pair_result.get("elapsed_seconds")
    solo_elapsed = solo_result.get("elapsed_seconds")
    if not isinstance(pair_elapsed, (int, float)) or not isinstance(solo_elapsed, (int, float)):
        return None
    if solo_elapsed <= 0:
        return None
    return pair_elapsed / solo_elapsed


def provider_limited(result: dict[str, Any] | None) -> bool:
    return result is not None and result.get("invoke_failure_reason") == "provider_limit"


def evaluate_fixture(
    fixture_dir: pathlib.Path,
    *,
    pair_arm: str,
    bare_max: int,
    solo_max: int,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float | None,
) -> dict[str, Any]:
    judge = load_json(fixture_dir / "judge.json")
    if judge is None:
        return {
            "fixture": fixture_dir.name,
            "status": "FAIL",
            "reason": "judge.json missing",
        }

    bare = score_for(judge, "bare")
    solo = score_for(judge, "solo_claude")
    pair = score_for(judge, pair_arm)
    solo_result = load_json(fixture_dir / "solo_claude" / "result.json")
    pair_result = load_json(fixture_dir / pair_arm / "result.json")
    ratio = elapsed_ratio(pair_result, solo_result)
    pair_provider_limited = provider_limited(pair_result)
    if pair_provider_limited:
        ratio = None

    reasons: list[str] = []
    if bare is None:
        reasons.append("bare score missing")
    elif bare > bare_max:
        reasons.append(f"bare score {bare} > {bare_max}")
    if solo is None:
        reasons.append("solo_claude score missing")
    elif solo > solo_max:
        reasons.append(f"solo_claude score {solo} > {solo_max}")
    if pair_provider_limited:
        pass
    elif pair is None:
        reasons.append(f"{pair_arm} score missing")
    elif solo is not None and pair - solo < min_pair_margin:
        reasons.append(f"{pair_arm} margin {pair - solo:+d} < +{min_pair_margin}")

    reasons.extend(clean_failures(fixture_dir, judge, "bare"))
    reasons.extend(clean_failures(fixture_dir, judge, "solo_claude"))
    reasons.extend(clean_failures(fixture_dir, judge, pair_arm))

    pair_mode = None if pair_result is None else pair_result.get("pair_mode")
    if pair_mode is not True and not pair_provider_limited:
        reasons.append(f"{pair_arm} pair_mode not true")

    if max_pair_solo_wall_ratio is not None and not pair_provider_limited:
        if ratio is None:
            reasons.append("pair/solo wall ratio missing")
        elif ratio > max_pair_solo_wall_ratio:
            reasons.append(f"pair/solo wall ratio {ratio:.2f} > {max_pair_solo_wall_ratio:.2f}")

    return {
        "fixture": fixture_dir.name,
        "status": "PASS" if not reasons else "FAIL",
        "bare_score": bare,
        "solo_score": solo,
        "pair_score": pair,
        "pair_margin": (
            None if pair_provider_limited
            else pair - solo if isinstance(pair, int) and isinstance(solo, int)
            else None
        ),
        "pair_mode": pair_mode,
        "pair_solo_wall_ratio": ratio,
        "reason": "; ".join(reasons),
    }


def fmt_ratio(value: Any) -> str:
    return f"{value:.2f}x" if isinstance(value, (int, float)) else "n/a"


def write_md(path: pathlib.Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Full-Pipeline Pair Gate - {report['run_id']}",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        f"Rule: at least {report['min_fixtures']} fixtures; bare <= {report['bare_max']}; "
        f"solo_claude <= {report['solo_max']}; {report['pair_arm']} clean; pair_mode true; "
        f"{report['pair_arm']} - solo_claude >= {report['min_pair_margin']}.",
        f"Max pair/solo wall ratio: {fmt_ratio(report['max_pair_solo_wall_ratio'])}",
        f"Average pair/solo wall ratio: {fmt_ratio(report['avg_pair_solo_wall_ratio'])}",
        "",
        "| Fixture | Bare | Solo | Pair | Margin | Pair mode | Wall ratio | Status | Reason |",
        "|---|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for row in report["rows"]:
        margin = row.get("pair_margin")
        margin_text = f"{margin:+d}" if isinstance(margin, int) else "n/a"
        lines.append(
            f"| {row['fixture']} | {row.get('bare_score')} | {row.get('solo_score')} | "
            f"{row.get('pair_score')} | {margin_text} | {str(row.get('pair_mode')).lower()} | "
            f"{fmt_ratio(row.get('pair_solo_wall_ratio'))} | {row['status']} | {row.get('reason', '')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf8")


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results", type=pathlib.Path)
    parser.add_argument("--bare-max", type=int, default=60)
    parser.add_argument("--solo-max", type=int, default=80)
    parser.add_argument("--min-pair-margin", type=int, default=5)
    parser.add_argument("--min-fixtures", type=int, default=2)
    parser.add_argument("--pair-arm", default="l2_gated")
    parser.add_argument("--max-pair-solo-wall-ratio", type=positive_float)
    parser.add_argument("--out-json", type=pathlib.Path)
    parser.add_argument("--out-md", type=pathlib.Path)
    args = parser.parse_args()

    run_root = args.results_root / args.run_id
    if not run_root.is_dir():
        print(f"no results dir: {run_root}", file=sys.stderr)
        return 2

    rows = [
        evaluate_fixture(
            fixture_dir,
            pair_arm=args.pair_arm,
            bare_max=args.bare_max,
            solo_max=args.solo_max,
            min_pair_margin=args.min_pair_margin,
            max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
        )
        for fixture_dir in sorted(p for p in run_root.iterdir() if p.is_dir())
    ]
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    fixture_count_ok = len(rows) >= args.min_fixtures
    verdict = "PASS" if rows and fixture_count_ok and pass_count == len(rows) else "FAIL"
    ratios = [
        row["pair_solo_wall_ratio"]
        for row in rows
        if isinstance(row.get("pair_solo_wall_ratio"), (int, float))
    ]
    report = {
        "run_id": args.run_id,
        "rule": "headroom candidates only; l2_gated must be clean, pair_mode true, and beat solo_claude by the configured margin",
        "verdict": verdict,
        "fixtures_total": len(rows),
        "fixtures_passed": pass_count,
        "min_fixtures": args.min_fixtures,
        "fixture_count_ok": fixture_count_ok,
        "bare_max": args.bare_max,
        "solo_max": args.solo_max,
        "min_pair_margin": args.min_pair_margin,
        "pair_arm": args.pair_arm,
        "max_pair_solo_wall_ratio": args.max_pair_solo_wall_ratio,
        "avg_pair_solo_wall_ratio": (sum(ratios) / len(ratios)) if ratios else None,
        "rows": rows,
    }

    if args.out_json:
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    if args.out_md:
        write_md(args.out_md, report)
    else:
        print(json.dumps(report, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
