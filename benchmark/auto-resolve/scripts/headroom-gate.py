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
import os
import pathlib
import re
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import is_score, loads_strict_json_object

KNOWN_ARMS = {"bare", "solo_claude"}
REJECTED_REGISTRY = pathlib.Path(__file__).with_name("pair-rejected-fixtures.sh")


def load_json(path: pathlib.Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        data = loads_strict_json_object(path.read_text())
    except (ValueError, json.JSONDecodeError):
        return None, "malformed"
    return data, None


def bool_flag_failure(value: object, true_reason: str, malformed_reason: str) -> str | None:
    if value is True:
        return true_reason
    if value is False or value is None:
        return None
    return malformed_reason


def fixture_short(name: str) -> str:
    return name.split("-", 1)[0] if "-" in name else name


def rejected_registry_path() -> pathlib.Path:
    override = os.environ.get("PAIR_REJECTED_FIXTURES_REGISTRY")
    return pathlib.Path(override) if override else REJECTED_REGISTRY


def load_rejected_short_ids(path: pathlib.Path) -> set[str]:
    if not path.is_file():
        raise ValueError(f"rejected fixture registry missing: {path}")
    rejected = set()
    for line in path.read_text().splitlines():
        match = re.match(r"\s*([FS]\d+)-\*\|([FS]\d+)\)", line)
        if match and match.group(1) == match.group(2):
            rejected.add(match.group(1))
    if not rejected:
        raise ValueError(f"rejected fixture registry has no fixture entries: {path}")
    return rejected


def score_for(judge: dict, arm: str) -> int | None:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return None
    if arm not in {mapped for slot, mapped in mapping.items() if slot in {"A", "B", "C"}}:
        return None
    raw_scores = judge.get("scores_by_arm")
    scores = raw_scores if isinstance(raw_scores, dict) else {}
    value = scores.get(arm)
    return value if is_score(value) else None


def axis_validation_counts(judge: dict) -> tuple[dict[str, int], int]:
    raw_mapping = judge.get("_blind_mapping")
    mapping = raw_mapping if isinstance(raw_mapping, dict) else {}
    raw_validation = judge.get("_axis_validation")
    validation = raw_validation if isinstance(raw_validation, dict) else {}
    cells = validation.get("out_of_range_cells") or []
    declared_count = validation.get("out_of_range_count")
    total_invalid = max(
        declared_count if isinstance(declared_count, int) else 0,
        len(cells) if isinstance(cells, list) else 0,
    )
    breakdown_to_letter = {
        "a_breakdown": "A",
        "b_breakdown": "B",
        "c_breakdown": "C",
    }
    counts: dict[str, int] = {}
    mapped_count = 0
    if not isinstance(cells, list):
        return counts, total_invalid
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        letter = breakdown_to_letter.get(cell.get("breakdown"))
        arm = mapping.get(letter) if letter else None
        if arm in KNOWN_ARMS:
            counts[arm] = counts.get(arm, 0) + 1
            mapped_count += 1
    return counts, max(0, total_invalid - mapped_count)


def axis_invalid_count(judge: dict, arm: str) -> int:
    counts, _ = axis_validation_counts(judge)
    return counts.get(arm, 0)


def axis_unmapped_invalid_count(judge: dict) -> int:
    _, unmapped = axis_validation_counts(judge)
    return unmapped


def blind_mapping_failures(judge: dict, required_arms: set[str]) -> list[str]:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return ["judge blind mapping missing"]
    mapped_arms = {arm for key, arm in mapping.items() if key in {"A", "B", "C"}}
    missing = sorted(required_arms - mapped_arms)
    if missing:
        return [f"judge blind mapping missing arm(s): {', '.join(missing)}"]
    return []


def arm_complete_failures(fixture_dir: pathlib.Path, judge: dict, arm: str) -> list[str]:
    failures: list[str] = []
    result, result_error = load_json(fixture_dir / arm / "result.json")
    verify, verify_error = load_json(fixture_dir / arm / "verify.json")
    diff = fixture_dir / arm / "diff.patch"
    if result_error:
        failures.append(f"{arm} result.json {result_error}")
    if verify_error:
        failures.append(f"{arm} verify.json {verify_error}")
    if not diff.is_file():
        failures.append(f"{arm} diff.patch missing")
    raw_dq_by_arm = judge.get("disqualifiers_by_arm")
    dq_by_arm = raw_dq_by_arm if isinstance(raw_dq_by_arm, dict) else {}
    dq_entry = dq_by_arm.get(arm)
    dq_value = dq_entry.get("disqualifier") if isinstance(dq_entry, dict) else dq_entry
    judge_dq_failure = bool_flag_failure(
        dq_value,
        f"{arm} judge disqualifier",
        f"{arm} judge disqualifier malformed",
    )
    if judge_dq_failure:
        failures.append(judge_dq_failure)
    axis_invalid = axis_invalid_count(judge, arm)
    if axis_invalid > 0:
        failures.append(f"{arm} judge axis-invalid ({axis_invalid})")
    if result is not None:
        for field, true_reason in (
            ("disqualifier", f"{arm} result disqualifier"),
            ("timed_out", f"{arm} timed out"),
            ("invoke_failure", f"{arm} invoke failure"),
            ("environment_contamination", f"{arm} environment contamination"),
        ):
            failure = bool_flag_failure(
                result.get(field),
                true_reason,
                f"{arm} result {field} malformed",
            )
            if failure:
                failures.append(failure)
    if verify is not None:
        verify_dq_failure = bool_flag_failure(
            verify.get("disqualifier"),
            f"{arm} verify disqualifier",
            f"{arm} verify disqualifier malformed",
        )
        if verify_dq_failure:
            failures.append(verify_dq_failure)
    return failures


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def remaining_headroom(score: int | None, max_score: int) -> int | None:
    return max_score - score if isinstance(score, int) else None


def average(values: list[int]) -> float | None:
    return (sum(values) / len(values)) if values else None


def fmt_float(value: float | None) -> str:
    return f"{value:.1f}" if isinstance(value, (int, float)) else "n/a"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results")
    parser.add_argument("--bare-max", type=int, default=60)
    parser.add_argument("--solo-max", type=int, default=80)
    parser.add_argument("--min-bare-headroom", type=non_negative_int, default=5)
    parser.add_argument("--min-solo-headroom", type=non_negative_int, default=5)
    parser.add_argument("--min-fixtures", type=positive_int, default=2)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)
    args = parser.parse_args()

    res_root = pathlib.Path(args.results_root) / args.run_id
    if not res_root.is_dir():
        print(f"no results dir: {res_root}", file=sys.stderr)
        return 2

    rows = []
    try:
        rejected_short_ids = load_rejected_short_ids(rejected_registry_path())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for fixture_dir in sorted(p for p in res_root.iterdir() if p.is_dir()):
        judge, judge_error = load_json(fixture_dir / "judge.json")
        if judge is None:
            rows.append({
                "fixture": fixture_dir.name,
                "status": "MISSING_JUDGE",
                "reason": f"judge.json {judge_error}",
            })
            continue
        bare = score_for(judge, "bare")
        solo = score_for(judge, "solo_claude")
        bare_headroom = remaining_headroom(bare, args.bare_max)
        solo_headroom = remaining_headroom(solo, args.solo_max)
        bare_complete_failures = arm_complete_failures(fixture_dir, judge, "bare")
        solo_complete_failures = arm_complete_failures(fixture_dir, judge, "solo_claude")
        unmapped_axis_invalid = axis_unmapped_invalid_count(judge)
        mapping_failures = blind_mapping_failures(judge, KNOWN_ARMS)
        rejected = fixture_short(fixture_dir.name) in rejected_short_ids
        bare_headroom_ok = (
            isinstance(bare_headroom, int)
            and bare_headroom >= args.min_bare_headroom
        )
        solo_headroom_ok = (
            isinstance(solo_headroom, int)
            and solo_headroom >= args.min_solo_headroom
        )
        bare_ok = (
            bare is not None
            and bare <= args.bare_max
            and bare_headroom_ok
            and not bare_complete_failures
        )
        solo_ok = (
            solo is not None
            and solo <= args.solo_max
            and solo_headroom_ok
            and not solo_complete_failures
        )
        judge_ok = unmapped_axis_invalid == 0 and not mapping_failures
        status = "PASS" if bare_ok and solo_ok and judge_ok and not rejected else "FAIL"
        reasons = []
        if bare is None:
            reasons.append("bare score missing")
        elif bare > args.bare_max:
            reasons.append(f"bare score {bare} > {args.bare_max}")
        elif bare_headroom is not None and bare_headroom < args.min_bare_headroom:
            reasons.append(
                f"bare headroom {bare_headroom} < {args.min_bare_headroom}"
            )
        if solo is None:
            reasons.append("solo_claude score missing")
        elif solo > args.solo_max:
            reasons.append(f"solo_claude score {solo} > {args.solo_max}")
        elif solo_headroom is not None and solo_headroom < args.min_solo_headroom:
            reasons.append(
                f"solo_claude headroom {solo_headroom} < {args.min_solo_headroom}"
            )
        if unmapped_axis_invalid > 0:
            reasons.append(f"judge axis-invalid unmapped ({unmapped_axis_invalid})")
        reasons.extend(mapping_failures)
        if rejected:
            reasons.append("fixture rejected for pair-candidate runs")
        reasons.extend(bare_complete_failures)
        reasons.extend(solo_complete_failures)
        rows.append({
            "fixture": fixture_dir.name,
            "status": status,
            "bare_score": bare,
            "solo_score": solo,
            "bare_headroom": bare_headroom,
            "solo_headroom": solo_headroom,
            "reason": "; ".join(reasons) if reasons else "",
        })

    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    fixture_count_ok = len(rows) >= args.min_fixtures
    verdict = "PASS" if pass_count == len(rows) and rows and fixture_count_ok else "FAIL"
    bare_headrooms = [
        value for row in rows
        if isinstance((value := row.get("bare_headroom")), int)
    ]
    solo_headrooms = [
        value for row in rows
        if isinstance((value := row.get("solo_headroom")), int)
    ]
    payload = {
        "run_id": args.run_id,
        "rule": (
            f"at least {args.min_fixtures} candidate fixtures; each must satisfy "
            f"bare <= {args.bare_max} with headroom >= {args.min_bare_headroom}, "
            f"solo_claude <= {args.solo_max} with headroom >= {args.min_solo_headroom}, "
            "with both baseline arms evidence-complete"
        ),
        "verdict": verdict,
        "fixtures_total": len(rows),
        "fixtures_passed": pass_count,
        "min_fixtures": args.min_fixtures,
        "bare_max": args.bare_max,
        "solo_max": args.solo_max,
        "min_bare_headroom_required": args.min_bare_headroom,
        "min_solo_headroom_required": args.min_solo_headroom,
        "fixture_count_ok": fixture_count_ok,
        "avg_bare_headroom": average(bare_headrooms),
        "min_bare_headroom": min(bare_headrooms) if bare_headrooms else None,
        "avg_solo_headroom": average(solo_headrooms),
        "min_solo_headroom": min(solo_headrooms) if solo_headrooms else None,
        "rows": rows,
    }

    if args.out_json:
        pathlib.Path(args.out_json).write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        f"# Headroom Gate — {args.run_id}",
        "",
        f"Verdict: **{verdict}**",
        "",
        f"Fixtures passed: {pass_count}/{len(rows)} (minimum required: {args.min_fixtures})",
        "",
        f"Rule: at least {args.min_fixtures} fixtures; bare <= {args.bare_max} "
        f"with headroom >= {args.min_bare_headroom}, solo_claude <= {args.solo_max} "
        f"with headroom >= {args.min_solo_headroom}, both baseline arms evidence-complete.",
        f"Average bare headroom: {fmt_float(payload['avg_bare_headroom'])}",
        f"Minimum bare headroom: {payload['min_bare_headroom'] if payload['min_bare_headroom'] is not None else 'n/a'}",
        f"Average solo_claude headroom: {fmt_float(payload['avg_solo_headroom'])}",
        f"Minimum solo_claude headroom: {payload['min_solo_headroom'] if payload['min_solo_headroom'] is not None else 'n/a'}",
        "",
        "| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Status | Reason |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['fixture']} | {row.get('bare_score')} | {row.get('bare_headroom')} | "
            f"{row.get('solo_score')} | {row.get('solo_headroom')} | {row['status']} | "
            f"{row.get('reason', '')} |"
        )
    report = "\n".join(lines) + "\n"
    if args.out_md:
        pathlib.Path(args.out_md).write_text(report)
    else:
        print(report)

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
