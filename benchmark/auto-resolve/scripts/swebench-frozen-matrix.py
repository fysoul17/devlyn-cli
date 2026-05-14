#!/usr/bin/env python3
"""Render a SWE-bench frozen VERIFY matrix from compare artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pair_evidence_contract import (
    all_known_pair_trigger_reasons,
    has_canonical_pair_trigger_reason,
    has_known_pair_trigger_reason,
    loads_strict_json_object,
    path_has_actionable_solo_headroom_hypothesis,
)


RANK = {
    "PASS": 0,
    "PASS_WITH_ISSUES": 1,
    "NEEDS_WORK": 2,
    "BLOCKED": 3,
}


def rank(verdict: str | None) -> int:
    return RANK.get(verdict or "", -1)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return loads_strict_json_object(path.read_text(encoding="utf8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def verdict_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def number_field(payload: dict[str, Any], key: str) -> int | float | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def transcript_failure_reason(results_root: Path, run_id: str, arm: str) -> str | None:
    transcript_path = results_root / run_id / arm / "transcript.txt"
    if not transcript_path.is_file():
        return None
    transcript = transcript_path.read_text(encoding="utf8", errors="replace")
    if "You've hit your limit" in transcript:
        return "provider_limit"
    return None


def infer_fixture_id(results_root: Path, run_id: str) -> str:
    for arm in ("pair", "solo"):
        input_path = results_root / run_id / arm / "input.md"
        if not input_path.exists():
            continue
        match = re.search(r"docs/roadmap/phase-1/([^`\s]+)\.md", input_path.read_text())
        if match:
            return match.group(1)
    return "unknown"


def elapsed_ratio(pair_elapsed: Any, solo_elapsed: Any) -> float | None:
    if not isinstance(pair_elapsed, (int, float)) or not isinstance(solo_elapsed, (int, float)):
        return None
    if pair_elapsed <= 0 or solo_elapsed <= 0:
        return None
    return pair_elapsed / solo_elapsed


def is_true(value: Any) -> bool:
    return value is True


def pair_trigger_failures(
    pair: dict[str, Any],
    *,
    fixture_spec: Path | None = None,
    require_hypothesis_trigger: bool = False,
) -> list[str]:
    trigger = pair.get("pair_trigger")
    if not isinstance(trigger, dict):
        return ["pair_trigger missing or malformed"]
    eligible = trigger.get("eligible")
    reasons = trigger.get("reasons")
    skipped_reason = trigger.get("skipped_reason")
    if not isinstance(eligible, bool):
        return ["pair_trigger.eligible malformed"]
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        return ["pair_trigger.reasons malformed"]
    if skipped_reason is not None and not isinstance(skipped_reason, str):
        return ["pair_trigger.skipped_reason malformed"]
    if eligible is True:
        failures = []
        if not reasons:
            failures.append("pair_trigger eligible with empty reasons")
        if reasons and not has_known_pair_trigger_reason(reasons):
            failures.append("pair_trigger reasons missing known trigger reason")
        if (
            reasons
            and has_known_pair_trigger_reason(reasons)
            and not all_known_pair_trigger_reasons(reasons)
        ):
            failures.append("pair_trigger reasons contain unknown trigger reason")
        if (
            reasons
            and all_known_pair_trigger_reasons(reasons)
            and not has_canonical_pair_trigger_reason(reasons)
        ):
            failures.append("pair_trigger reasons missing canonical trigger reason")
        if skipped_reason is not None:
            failures.append("pair_trigger eligible with skipped_reason")
        if (
            require_hypothesis_trigger
            and fixture_spec is not None
            and path_has_actionable_solo_headroom_hypothesis(fixture_spec)
            and "spec.solo_headroom_hypothesis" not in reasons
        ):
            failures.append("pair_trigger missing spec.solo_headroom_hypothesis")
        return failures
    if reasons:
        return ["pair_trigger ineligible with reasons"]
    return []


def pair_trigger_eligible(pair: dict[str, Any]) -> bool:
    trigger = pair.get("pair_trigger")
    return (
        isinstance(trigger, dict)
        and trigger.get("eligible") is True
        and isinstance(trigger.get("reasons"), list)
        and all(isinstance(reason, str) for reason in trigger["reasons"])
        and len(trigger["reasons"]) > 0
        and all_known_pair_trigger_reasons(trigger["reasons"])
        and has_canonical_pair_trigger_reason(trigger["reasons"])
        and trigger.get("skipped_reason") is None
    )


def pair_trigger_reasons(pair: dict[str, Any]) -> list[str]:
    trigger = pair.get("pair_trigger")
    if not isinstance(trigger, dict):
        return []
    reasons = trigger.get("reasons")
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        return []
    return reasons


def pair_trigger_label(row: dict[str, Any]) -> str:
    if row["pair_trigger_missed"]:
        return "missed"
    failures = row.get("pair_trigger_failures") or []
    if failures:
        return "malformed"
    if row["pair_trigger_eligible"]:
        return "eligible"
    return "not_eligible"


def load_gate_rows(gate_json: Path | None) -> dict[str, dict[str, Any]]:
    if gate_json is None:
        return {}
    doc = load_json(gate_json)
    rows = doc.get("rows")
    if not isinstance(rows, list):
        return {}
    return {
        row["run_id"]: row for row in rows
        if isinstance(row, dict) and isinstance(row.get("run_id"), str)
    }


def min_gate_rate(value: str) -> float:
    rate = float(value)
    if rate < 0 or rate > 1:
        raise argparse.ArgumentTypeError("--min-gate-rate must be between 0 and 1")
    return rate


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def classify(row: dict[str, Any], included: bool) -> str:
    if included:
        external = row["external_lift"]
        internal = row["internal_lift"]
        if external and internal:
            return "gate: external + internal lift"
        if external:
            return "gate: external lift"
        if internal:
            return "gate: internal lift"
        return "gate"
    if row.get("row_failed_before_compare"):
        row_exit = row.get("row_exit")
        suffix = f" exit={row_exit}" if isinstance(row_exit, int) else ""
        return f"failed attempt: row runner{suffix}"
    if row.get("compare_missing"):
        return "failed attempt: missing compare"
    if row.get("solo_timed_out") or row.get("pair_timed_out"):
        return "failed attempt: timeout"
    if row.get("solo_failure_reason") == "provider_limit" or row.get("pair_failure_reason") == "provider_limit":
        return "failed attempt: provider limit"
    if row.get("solo_environment_contamination") or row.get("pair_environment_contamination"):
        return "failed attempt: environment contamination"
    if row.get("solo_disqualifier") or row.get("pair_disqualifier"):
        return "failed attempt: disqualifier"
    if row.get("solo_invoke_failure") or row.get("pair_invoke_failure"):
        return "failed attempt: invoke failure"
    if row.get("solo_invoke_exit") not in (None, 0) or row.get("pair_invoke_exit") not in (None, 0):
        return "failed attempt: nonzero invoke exit"
    if row.get("malformed_compare"):
        return "failed attempt: malformed compare"
    if row.get("pair_trigger_missed"):
        return "failed attempt: pair trigger missed"
    trigger_failures = row.get("pair_trigger_failures") or []
    if trigger_failures:
        return "failed attempt: pair trigger contract: " + "; ".join(trigger_failures)
    if row["solo_mechanical"] == "FAIL":
        return "excluded: solo mechanical dominated"
    if row["external_lift"] or row["internal_lift"]:
        failures = row.get("gate_failures") or []
        if failures:
            return "lift excluded: " + "; ".join(failures)
        return "lift outside gate"
    if rank(row["pair_verdict"]) > rank(row["solo_verdict"]):
        return "recall-only advisory"
    if row["pair_found_more_low_or_worse"] or row["pair_found_more_findings"]:
        return "recall-only findings"
    return "no verdict lift"


def build_row(
    results_root: Path,
    run_id: str,
    gate_rows_by_id: dict[str, dict[str, Any]],
    *,
    fixtures_root: Path | None,
    require_hypothesis_trigger: bool,
) -> dict[str, Any]:
    compare_path = results_root / run_id / "compare.json"
    malformed_compare = False
    if compare_path.exists():
        compare = load_json(compare_path)
        malformed_compare = not bool(compare)
    else:
        compare = {
            "solo": {},
            "pair": {},
            "comparison": {"compare_missing": True},
        }
    solo = object_field(compare, "solo")
    pair = object_field(compare, "pair")
    comparison = object_field(compare, "comparison")
    malformed_compare = malformed_compare or any(
        key in compare and not isinstance(compare.get(key), dict)
        for key in ("solo", "pair", "comparison")
    )
    pair_ratio = elapsed_ratio(
        number_field(pair, "elapsed_seconds"),
        number_field(solo, "elapsed_seconds"),
    )
    gate_row = gate_rows_by_id.get(run_id) or {}
    solo_verdict = (
        verdict_field(comparison, "solo_verdict")
        or verdict_field(solo, "verify_verdict")
    )
    pair_verdict = (
        verdict_field(comparison, "pair_verdict")
        or verdict_field(pair, "verify_verdict")
    )
    solo_sub = object_field(solo, "sub_verdicts")
    pair_sub = object_field(pair, "sub_verdicts")
    fixture_id = infer_fixture_id(results_root, run_id)
    fixture_spec = None
    if fixtures_root is not None and fixture_id != "unknown":
        fixture_spec = fixtures_root / fixture_id / "spec.md"
    trigger_failures = pair_trigger_failures(
        pair,
        fixture_spec=fixture_spec,
        require_hypothesis_trigger=require_hypothesis_trigger,
    )
    trigger_reasons = pair_trigger_reasons(pair)
    row = {
        "fixture_id": fixture_id,
        "run_id": run_id,
        "solo_verdict": solo_verdict,
        "pair_verdict": pair_verdict,
        "pair_mode": is_true(pair.get("pair_mode")),
        "pair_trigger_eligible": pair_trigger_eligible(pair),
        "pair_trigger_reasons": trigger_reasons,
        "pair_trigger_has_canonical_reason": has_canonical_pair_trigger_reason(trigger_reasons),
        "pair_trigger_missed": is_true(comparison.get("pair_trigger_missed")),
        "pair_trigger_failures": trigger_failures,
        "external_lift": is_true(comparison.get("pair_verdict_lift")),
        "internal_lift": is_true(comparison.get("pair_internal_verdict_lift")),
        "pair_found_more_findings": is_true(comparison.get("pair_found_more_findings")),
        "pair_found_more_low_or_worse": is_true(comparison.get("pair_found_more_low_or_worse")),
        "row_failed_before_compare": is_true(comparison.get("row_failed_before_compare")),
        "row_exit": comparison.get("row_exit"),
        "compare_missing": is_true(comparison.get("compare_missing")),
        "solo_invoke_exit": solo.get("invoke_exit"),
        "pair_invoke_exit": pair.get("invoke_exit"),
        "solo_failure_reason": solo.get("invoke_failure_reason")
        or transcript_failure_reason(results_root, run_id, "solo"),
        "pair_failure_reason": pair.get("invoke_failure_reason")
        or transcript_failure_reason(results_root, run_id, "pair"),
        "solo_invoke_failure": is_true(solo.get("invoke_failure")),
        "pair_invoke_failure": is_true(pair.get("invoke_failure")),
        "solo_environment_contamination": is_true(solo.get("environment_contamination")),
        "pair_environment_contamination": is_true(pair.get("environment_contamination")),
        "solo_disqualifier": is_true(solo.get("disqualifier")),
        "pair_disqualifier": is_true(pair.get("disqualifier")),
        "solo_timed_out": is_true(solo.get("timed_out")),
        "pair_timed_out": is_true(pair.get("timed_out")),
        "pair_solo_wall_ratio": pair_ratio,
        "solo_mechanical": verdict_field(solo_sub, "mechanical"),
        "pair_mechanical": verdict_field(pair_sub, "mechanical"),
        "included_in_gate": gate_row.get("status") == "PASS",
        "gate_failures": gate_row.get("failures") or [],
        "malformed_compare": malformed_compare,
    }
    row["classification"] = classify(row, row["included_in_gate"])
    return row


def fmt_ratio(value: Any) -> str:
    return f"{value:.2f}x" if isinstance(value, (int, float)) else "n/a"


def fmt_trigger_reasons(value: Any) -> str:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return ""
    return ",".join(value)


def write_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# {report['title']}",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        f"Runs: {report['runs_total']}",
        f"Included in gate: {report['gate_rows']}",
        f"Excluded/recall/no-lift: {report['excluded_or_recall_rows']}",
        f"Gate rate: {report['gate_rate']:.3f}",
        f"Trailing non-gate rows: {report['trailing_non_gate_rows']}",
    ]
    if report["yield_thresholds"]:
        lines.extend(["", f"Yield verdict: **{report['yield_verdict']}**"])
        if report["yield_failures"]:
            lines.append("Yield failures:")
            lines.extend(f"- {failure}" for failure in report["yield_failures"])
    if report.get("gate_artifact_json"):
        lines.extend(["", f"Gate artifact: `{report['gate_artifact_json']}`"])
    lines.extend(["", "Classification counts:"])
    for name, count in sorted(report["classification_counts"].items()):
        lines.append(f"- {name}: {count}")
    lines.extend(
        [
            "",
            "| Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Pair trigger | Triggers | Wall ratio | External lift | Internal lift | Included | Classification |",
            "|---|---|---|---|---|---|---:|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['fixture_id']} | {row['solo_verdict']} | {row['pair_verdict']} | "
            f"{str(row['pair_mode']).lower()} | {pair_trigger_label(row)} | "
            f"{fmt_trigger_reasons(row.get('pair_trigger_reasons'))} | "
            f"{fmt_ratio(row.get('pair_solo_wall_ratio'))} | "
            f"{str(row['external_lift']).lower()} | {str(row['internal_lift']).lower()} | "
            f"{str(row['included_in_gate']).lower()} | {row['classification']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results", type=Path)
    parser.add_argument("--fixtures-root", type=Path)
    parser.add_argument("--run-id", action="append", required=True)
    parser.add_argument("--gate-json", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--verdict", required=True)
    parser.add_argument("--min-gate-rate", type=min_gate_rate)
    parser.add_argument("--max-trailing-non-gate", type=non_negative_int)
    parser.add_argument(
        "--require-hypothesis-trigger",
        action="store_true",
        help="require fixtures with actionable solo-headroom hypotheses to expose spec.solo_headroom_hypothesis in pair_trigger.reasons",
    )
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    args = parser.parse_args()
    if args.require_hypothesis_trigger and args.fixtures_root is None:
        parser.error("--require-hypothesis-trigger requires --fixtures-root")

    gate_rows_by_id = load_gate_rows(args.gate_json)
    rows = [
        build_row(
            args.results_root,
            run_id,
            gate_rows_by_id,
            fixtures_root=args.fixtures_root,
            require_hypothesis_trigger=args.require_hypothesis_trigger,
        )
        for run_id in args.run_id
    ]
    gate_rows = sum(1 for row in rows if row["included_in_gate"])
    trailing_non_gate_rows = 0
    for row in reversed(rows):
        if row["included_in_gate"]:
            break
        trailing_non_gate_rows += 1
    gate_rate = gate_rows / len(rows) if rows else 0.0
    yield_thresholds = {
        "min_gate_rate": args.min_gate_rate,
        "max_trailing_non_gate": args.max_trailing_non_gate,
    }
    thresholds_configured = any(value is not None for value in yield_thresholds.values())
    yield_failures = []
    if args.min_gate_rate is not None and gate_rate < args.min_gate_rate:
        yield_failures.append(f"gate rate {gate_rate:.3f} < minimum {args.min_gate_rate:.3f}")
    if args.max_trailing_non_gate is not None and trailing_non_gate_rows > args.max_trailing_non_gate:
        yield_failures.append(
            f"trailing non-gate rows {trailing_non_gate_rows} > maximum {args.max_trailing_non_gate}"
        )
    report = {
        "title": args.title,
        "verdict": args.verdict,
        "runs_total": len(rows),
        "gate_rows": gate_rows,
        "excluded_or_recall_rows": len(rows) - gate_rows,
        "gate_rate": gate_rate,
        "trailing_non_gate_rows": trailing_non_gate_rows,
        "classification_counts": dict(Counter(row["classification"] for row in rows)),
        "yield_thresholds": {
            key: value for key, value in yield_thresholds.items() if value is not None
        },
        "yield_verdict": "FAIL" if yield_failures else "PASS" if thresholds_configured else "NOT_CONFIGURED",
        "yield_failures": yield_failures,
        "gate_artifact_json": str(args.gate_json) if args.gate_json else None,
        "rows": rows,
    }
    args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    write_md(args.out_md, report)
    print(json.dumps(report, indent=2))
    return 2 if yield_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
