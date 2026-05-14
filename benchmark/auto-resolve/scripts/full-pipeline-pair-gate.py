#!/usr/bin/env python3
"""Gate full-pipeline L2/pair evidence against L1 solo.

This is stricter than headroom-gate.py. Headroom only says a candidate set is
worth measuring. This gate says the measured L2 arm is usable evidence:
bare and solo leave headroom with complete comparable artifacts, the selected
pair arm is evidence-clean, pair mode actually fired for a canonical trigger
reason, and the blind judge scores the selected pair arm materially above
solo_claude.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
FIXTURES_ROOT = SCRIPT_DIR.parent / "fixtures"

from pair_evidence_contract import (
    ALLOWED_PAIR_ARMS,
    all_known_pair_trigger_reasons,
    has_canonical_pair_trigger_reason,
    has_known_pair_trigger_reason,
    is_score,
    is_strict_number,
    loads_strict_json_object,
    path_has_actionable_solo_headroom_hypothesis,
)

KNOWN_ARMS = {"bare", "solo_claude"} | ALLOWED_PAIR_ARMS
PASS_VERDICTS = {"PASS", "PASS_WITH_ISSUES"}
REJECTED_REGISTRY = pathlib.Path(__file__).with_name("pair-rejected-fixtures.sh")


def load_json(path: pathlib.Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        data = loads_strict_json_object(path.read_text())
    except (ValueError, json.JSONDecodeError):
        return None, "malformed"
    return data, None


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


def score_for(judge: dict[str, Any], arm: str) -> int | None:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return None
    if arm not in {mapped for slot, mapped in mapping.items() if slot in {"A", "B", "C"}}:
        return None
    raw_scores = judge.get("scores_by_arm")
    scores = raw_scores if isinstance(raw_scores, dict) else {}
    value = scores.get(arm)
    return value if is_score(value) else None


def verify_score_clean(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    value = payload.get("verify_score")
    return is_strict_number(value) and value >= 1.0


def bool_flag_failure(value: Any, true_reason: str, malformed_reason: str) -> str | None:
    if value is True:
        return true_reason
    if value is False or value is None:
        return None
    return malformed_reason


def pair_trigger_failures(result: dict[str, Any] | None, arm: str) -> list[str]:
    if result is None:
        return []
    trigger = result.get("pair_trigger")
    if not isinstance(trigger, dict):
        return [f"{arm} pair_trigger missing or malformed"]
    eligible = trigger.get("eligible")
    reasons = trigger.get("reasons")
    skipped_reason = trigger.get("skipped_reason")
    if not isinstance(eligible, bool):
        return [f"{arm} pair_trigger.eligible malformed"]
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        return [f"{arm} pair_trigger.reasons malformed"]
    if skipped_reason is not None and not isinstance(skipped_reason, str):
        return [f"{arm} pair_trigger.skipped_reason malformed"]
    if eligible is not True:
        return [f"{arm} pair_trigger not eligible"]
    if not reasons:
        return [f"{arm} pair_trigger eligible with empty reasons"]
    if not has_known_pair_trigger_reason(reasons):
        return [f"{arm} pair_trigger reasons missing known trigger reason"]
    if not all_known_pair_trigger_reasons(reasons):
        return [f"{arm} pair_trigger reasons contain unknown trigger reason"]
    if not has_canonical_pair_trigger_reason(reasons):
        return [f"{arm} pair_trigger reasons missing canonical trigger reason"]
    if skipped_reason is not None:
        return [f"{arm} pair_trigger eligible with skipped_reason"]
    return []


def pair_trigger_eligible(result: dict[str, Any] | None) -> bool:
    if result is None:
        return False
    trigger = result.get("pair_trigger")
    return (
        isinstance(trigger, dict)
        and trigger.get("eligible") is True
        and isinstance(trigger.get("reasons"), list)
        and bool(trigger.get("reasons"))
        and all(isinstance(reason, str) for reason in trigger.get("reasons", []))
        and all_known_pair_trigger_reasons(trigger.get("reasons", []))
        and has_canonical_pair_trigger_reason(trigger.get("reasons", []))
        and trigger.get("skipped_reason") is None
    )


def pair_trigger_reasons(result: dict[str, Any] | None) -> list[str]:
    if result is None:
        return []
    trigger = result.get("pair_trigger")
    if not isinstance(trigger, dict):
        return []
    reasons = trigger.get("reasons")
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        return []
    return reasons


def fixture_spec_has_solo_headroom_hypothesis(fixture: str) -> bool:
    return path_has_actionable_solo_headroom_hypothesis(FIXTURES_ROOT / fixture / "spec.md")


def skill_verdict_failures(result: dict[str, Any] | None, arm: str) -> list[str]:
    if result is None or arm == "bare":
        return []
    failures: list[str] = []
    terminal = result.get("terminal_verdict")
    verify = result.get("verify_verdict")
    if terminal not in PASS_VERDICTS:
        failures.append(f"{arm} terminal verdict not pass")
    if verify not in PASS_VERDICTS:
        failures.append(f"{arm} verify verdict not pass")
    return failures


def axis_validation_counts(judge: dict[str, Any]) -> tuple[dict[str, int], int]:
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


def axis_invalid_count(judge: dict[str, Any], arm: str) -> int:
    counts, _ = axis_validation_counts(judge)
    return counts.get(arm, 0)


def axis_unmapped_invalid_count(judge: dict[str, Any]) -> int:
    _, unmapped = axis_validation_counts(judge)
    return unmapped


def blind_mapping_failures(judge: dict[str, Any], required_arms: set[str]) -> list[str]:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return ["judge blind mapping missing"]
    mapped_arms = {arm for key, arm in mapping.items() if key in {"A", "B", "C"}}
    missing = sorted(required_arms - mapped_arms)
    if missing:
        return [f"judge blind mapping missing arm(s): {', '.join(missing)}"]
    return []


def clean_failures(
    fixture_dir: pathlib.Path,
    judge: dict[str, Any],
    arm: str,
    *,
    require_correctness: bool,
) -> list[str]:
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
            ("environment_contamination", f"{arm} environment contamination"),
        ):
            failure = bool_flag_failure(
                result.get(field),
                true_reason,
                f"{arm} result {field} malformed",
            )
            if failure:
                failures.append(failure)
        invoke_failure = bool_flag_failure(
            result.get("invoke_failure"),
            f"{arm} invoke failure",
            f"{arm} result invoke_failure malformed",
        )
        if invoke_failure == f"{arm} invoke failure":
            reason = result.get("invoke_failure_reason")
            if isinstance(reason, str) and reason:
                failures.append(f"{arm} invoke failure ({reason})")
            else:
                failures.append(invoke_failure)
        elif invoke_failure:
            failures.append(invoke_failure)
        if require_correctness:
            failures.extend(skill_verdict_failures(result, arm))
    if verify is not None:
        verify_dq_failure = bool_flag_failure(
            verify.get("disqualifier"),
            f"{arm} verify disqualifier",
            f"{arm} verify disqualifier malformed",
        )
        if verify_dq_failure:
            failures.append(verify_dq_failure)
    if require_correctness and verify is not None and not verify_score_clean(verify):
        failures.append(f"{arm} verify_score < 1.0")
    return failures


def elapsed_ratio(pair_result: dict[str, Any] | None, solo_result: dict[str, Any] | None) -> float | None:
    if pair_result is None or solo_result is None:
        return None
    pair_elapsed = pair_result.get("elapsed_seconds")
    solo_elapsed = solo_result.get("elapsed_seconds")
    if not is_strict_number(pair_elapsed) or not is_strict_number(solo_elapsed):
        return None
    return pair_elapsed / solo_elapsed


def provider_limited(result: dict[str, Any] | None) -> bool:
    return result is not None and result.get("invoke_failure_reason") == "provider_limit"


def evaluate_fixture(
    fixture_dir: pathlib.Path,
    *,
    rejected_short_ids: set[str],
    pair_arm: str,
    bare_max: int,
    solo_max: int,
    min_bare_headroom: int,
    min_solo_headroom: int,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float | None,
    require_hypothesis_trigger: bool,
) -> dict[str, Any]:
    judge, judge_error = load_json(fixture_dir / "judge.json")
    if judge is None:
        return {
            "fixture": fixture_dir.name,
            "status": "FAIL",
            "reason": f"judge.json {judge_error}",
        }

    bare = score_for(judge, "bare")
    solo = score_for(judge, "solo_claude")
    pair = score_for(judge, pair_arm)
    bare_headroom = bare_max - bare if isinstance(bare, int) else None
    solo_headroom = solo_max - solo if isinstance(solo, int) else None
    solo_result, _ = load_json(fixture_dir / "solo_claude" / "result.json")
    pair_result, _ = load_json(fixture_dir / pair_arm / "result.json")
    ratio = elapsed_ratio(pair_result, solo_result)
    pair_provider_limited = provider_limited(pair_result)
    if pair_provider_limited:
        ratio = None

    reasons: list[str] = []
    if fixture_short(fixture_dir.name) in rejected_short_ids:
        reasons.append("fixture rejected for pair-candidate runs")
    if bare is None:
        reasons.append("bare score missing")
    elif bare > bare_max:
        reasons.append(f"bare score {bare} > {bare_max}")
    elif bare_headroom is not None and bare_headroom < min_bare_headroom:
        reasons.append(f"bare headroom {bare_headroom} < {min_bare_headroom}")
    if solo is None:
        reasons.append("solo_claude score missing")
    elif solo > solo_max:
        reasons.append(f"solo_claude score {solo} > {solo_max}")
    elif solo_headroom is not None and solo_headroom < min_solo_headroom:
        reasons.append(f"solo_claude headroom {solo_headroom} < {min_solo_headroom}")
    if pair_provider_limited:
        pass
    elif pair is None:
        reasons.append(f"{pair_arm} score missing")
    elif solo is not None and pair - solo < min_pair_margin:
        reasons.append(f"{pair_arm} margin {pair - solo:+d} < +{min_pair_margin}")
    unmapped_axis_invalid = axis_unmapped_invalid_count(judge)
    if unmapped_axis_invalid > 0:
        reasons.append(f"judge axis-invalid unmapped ({unmapped_axis_invalid})")
    reasons.extend(blind_mapping_failures(judge, {"bare", "solo_claude", pair_arm}))

    reasons.extend(clean_failures(fixture_dir, judge, "bare", require_correctness=False))
    reasons.extend(clean_failures(fixture_dir, judge, "solo_claude", require_correctness=False))
    reasons.extend(clean_failures(fixture_dir, judge, pair_arm, require_correctness=True))

    pair_mode = None if pair_result is None else pair_result.get("pair_mode")
    if pair_mode is not True and not pair_provider_limited:
        reasons.append(f"{pair_arm} pair_mode not true")
    if not pair_provider_limited:
        reasons.extend(pair_trigger_failures(pair_result, pair_arm))
        if (
            require_hypothesis_trigger
            and
            fixture_spec_has_solo_headroom_hypothesis(fixture_dir.name)
            and "spec.solo_headroom_hypothesis" not in pair_trigger_reasons(pair_result)
        ):
            reasons.append(f"{pair_arm} pair_trigger missing spec.solo_headroom_hypothesis")

    if max_pair_solo_wall_ratio is not None and not pair_provider_limited:
        if ratio is None:
            reasons.append("pair/solo wall ratio missing")
        elif ratio > max_pair_solo_wall_ratio:
            reasons.append(f"pair/solo wall ratio {ratio:.2f} > {max_pair_solo_wall_ratio:.2f}")

    return {
        "fixture": fixture_dir.name,
        "status": "PASS" if not reasons else "FAIL",
        "bare_score": bare,
        "bare_headroom": bare_headroom,
        "solo_score": solo,
        "solo_headroom": solo_headroom,
        "pair_score": pair,
        "pair_margin": (
            None if pair_provider_limited
            else pair - solo if isinstance(pair, int) and isinstance(solo, int)
            else None
        ),
        "pair_mode": pair_mode,
        "pair_trigger_eligible": pair_trigger_eligible(pair_result),
        "pair_trigger_reasons": pair_trigger_reasons(pair_result),
        "pair_trigger_has_canonical_reason": has_canonical_pair_trigger_reason(
            pair_trigger_reasons(pair_result)
        ),
        "pair_trigger_has_hypothesis_reason": (
            "spec.solo_headroom_hypothesis" in pair_trigger_reasons(pair_result)
        ),
        "pair_solo_wall_ratio": ratio,
        "reason": "; ".join(reasons),
    }


def fmt_ratio(value: Any) -> str:
    return f"{value:.2f}x" if isinstance(value, (int, float)) else "n/a"


def fmt_margin(value: Any) -> str:
    return f"{value:+.1f}" if isinstance(value, (int, float)) else "n/a"


def fmt_trigger_reasons(value: Any) -> str:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return ""
    return ",".join(value)


def write_md(path: pathlib.Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Full-Pipeline Pair Gate - {report['run_id']}",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        f"Fixtures passed: {report['fixtures_passed']}/{report['fixtures_total']} "
        f"(minimum required: {report['min_fixtures']})",
        "",
        f"Rule: at least {report['min_fixtures']} fixtures; bare <= {report['bare_max']}; "
        f"bare headroom >= {report['min_bare_headroom_required']}; "
        f"solo_claude <= {report['solo_max']}; "
        f"solo_claude headroom >= {report['min_solo_headroom_required']}; "
        f"{report['pair_arm']} evidence-clean; pair_mode true; "
        "pair_trigger eligible with canonical reason; "
        f"{report['pair_arm']} - solo_claude >= {report['min_pair_margin']}.",
        f"Average pair margin: {fmt_margin(report['avg_pair_margin'])}",
        f"Allowed pair/solo wall ratio: {fmt_ratio(report['max_pair_solo_wall_ratio'])}",
        f"Maximum observed pair/solo wall ratio: {fmt_ratio(report['max_observed_pair_solo_wall_ratio'])}",
        f"Average pair/solo wall ratio: {fmt_ratio(report['avg_pair_solo_wall_ratio'])}",
        f"Hypothesis trigger required: {str(report['require_hypothesis_trigger']).lower()}",
        "",
        "| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Pair | Margin | Pair mode | Hypothesis trigger | Triggers | Wall ratio | Status | Reason |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|---|",
    ]
    for row in report["rows"]:
        margin = row.get("pair_margin")
        margin_text = f"{margin:+d}" if isinstance(margin, int) else "n/a"
        lines.append(
            f"| {row['fixture']} | {row.get('bare_score')} | {row.get('bare_headroom')} | "
            f"{row.get('solo_score')} | {row.get('solo_headroom')} | "
            f"{row.get('pair_score')} | {margin_text} | {str(row.get('pair_mode')).lower()} | "
            f"{str(row.get('pair_trigger_has_hypothesis_reason')).lower()} | "
            f"{fmt_trigger_reasons(row.get('pair_trigger_reasons'))} | "
            f"{fmt_ratio(row.get('pair_solo_wall_ratio'))} | {row['status']} | {row.get('reason', '')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf8")


def positive_float(value: str) -> float:
    parsed = float(value)
    if not is_strict_number(parsed):
        raise argparse.ArgumentTypeError("value must be finite and > 0")
    return parsed


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results", type=pathlib.Path)
    parser.add_argument("--bare-max", type=int, default=60)
    parser.add_argument("--solo-max", type=int, default=80)
    parser.add_argument("--min-bare-headroom", type=non_negative_int, default=5)
    parser.add_argument("--min-solo-headroom", type=non_negative_int, default=5)
    parser.add_argument("--min-pair-margin", type=positive_int, default=5)
    parser.add_argument("--min-fixtures", type=positive_int, default=2)
    parser.add_argument("--pair-arm", default="l2_risk_probes")
    parser.add_argument("--max-pair-solo-wall-ratio", type=positive_float, default=3.0)
    parser.add_argument(
        "--require-hypothesis-trigger",
        action="store_true",
        help="require fixtures with actionable solo-headroom hypotheses to expose spec.solo_headroom_hypothesis in pair_trigger.reasons",
    )
    parser.add_argument("--out-json", type=pathlib.Path)
    parser.add_argument("--out-md", type=pathlib.Path)
    args = parser.parse_args()

    if args.pair_arm == "l2_forced":
        print(
            "pair-arm l2_forced is retired: it leaks pair-awareness before IMPLEMENT; "
            "use l2_risk_probes for current proof runs or l2_gated for diagnostics.",
            file=sys.stderr,
        )
        return 2
    if args.pair_arm not in ALLOWED_PAIR_ARMS:
        print(
            f"pair-arm must be one of {sorted(ALLOWED_PAIR_ARMS)}: {args.pair_arm}",
            file=sys.stderr,
        )
        return 2

    run_root = args.results_root / args.run_id
    if not run_root.is_dir():
        print(f"no results dir: {run_root}", file=sys.stderr)
        return 2

    try:
        rejected_short_ids = load_rejected_short_ids(rejected_registry_path())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rows = [
        evaluate_fixture(
            fixture_dir,
            rejected_short_ids=rejected_short_ids,
            pair_arm=args.pair_arm,
            bare_max=args.bare_max,
            solo_max=args.solo_max,
            min_bare_headroom=args.min_bare_headroom,
            min_solo_headroom=args.min_solo_headroom,
            min_pair_margin=args.min_pair_margin,
            max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
            require_hypothesis_trigger=args.require_hypothesis_trigger,
        )
        for fixture_dir in sorted(p for p in run_root.iterdir() if p.is_dir())
    ]
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    fixture_count_ok = len(rows) >= args.min_fixtures
    verdict = "PASS" if rows and fixture_count_ok and pass_count == len(rows) else "FAIL"
    ratios = [
        row["pair_solo_wall_ratio"]
        for row in rows
        if is_strict_number(row.get("pair_solo_wall_ratio"))
    ]
    margins = [
        row["pair_margin"]
        for row in rows
        if isinstance(row.get("pair_margin"), int)
    ]
    rule = (
        "headroom candidates only; "
        f"bare headroom >= {args.min_bare_headroom}; "
        f"solo_claude headroom >= {args.min_solo_headroom}; "
        f"{args.pair_arm} must be evidence-clean, pair_mode true, "
        "pair_trigger eligible with a canonical reason, and beat solo_claude "
        "by the configured margin"
    )
    report = {
        "run_id": args.run_id,
        "rule": rule,
        "verdict": verdict,
        "fixtures_total": len(rows),
        "fixtures_passed": pass_count,
        "min_fixtures": args.min_fixtures,
        "fixture_count_ok": fixture_count_ok,
        "bare_max": args.bare_max,
        "solo_max": args.solo_max,
        "min_bare_headroom_required": args.min_bare_headroom,
        "min_solo_headroom_required": args.min_solo_headroom,
        "min_pair_margin": args.min_pair_margin,
        "pair_arm": args.pair_arm,
        "require_hypothesis_trigger": args.require_hypothesis_trigger,
        "max_pair_solo_wall_ratio": args.max_pair_solo_wall_ratio,
        "max_observed_pair_solo_wall_ratio": max(ratios) if ratios else None,
        "avg_pair_margin": (sum(margins) / len(margins)) if margins else None,
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
