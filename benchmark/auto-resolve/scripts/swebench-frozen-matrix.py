#!/usr/bin/env python3
"""Render a SWE-bench frozen VERIFY matrix from compare artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


RANK = {
    "PASS": 0,
    "PASS_WITH_ISSUES": 1,
    "NEEDS_WORK": 2,
    "BLOCKED": 3,
}


def rank(verdict: str | None) -> int:
    return RANK.get(verdict or "", -1)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf8"))


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
    if solo_elapsed <= 0:
        return None
    return pair_elapsed / solo_elapsed


def load_gate_rows(gate_json: Path | None) -> dict[str, dict[str, Any]]:
    if gate_json is None:
        return {}
    doc = load_json(gate_json)
    return {row["run_id"]: row for row in doc.get("rows", [])}


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
    if row.get("solo_invoke_exit") not in (None, 0) or row.get("pair_invoke_exit") not in (None, 0):
        return "failed attempt: nonzero invoke exit"
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


def build_row(results_root: Path, run_id: str, gate_rows_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    compare_path = results_root / run_id / "compare.json"
    if compare_path.exists():
        compare = load_json(compare_path)
    else:
        compare = {
            "solo": {},
            "pair": {},
            "comparison": {"compare_missing": True},
        }
    solo = compare.get("solo") or {}
    pair = compare.get("pair") or {}
    comparison = compare.get("comparison") or {}
    pair_ratio = elapsed_ratio(pair.get("elapsed_seconds"), solo.get("elapsed_seconds"))
    gate_row = gate_rows_by_id.get(run_id) or {}
    row = {
        "fixture_id": infer_fixture_id(results_root, run_id),
        "run_id": run_id,
        "solo_verdict": comparison.get("solo_verdict") or solo.get("verify_verdict"),
        "pair_verdict": comparison.get("pair_verdict") or pair.get("verify_verdict"),
        "pair_mode": bool(pair.get("pair_mode")),
        "external_lift": bool(comparison.get("pair_verdict_lift")),
        "internal_lift": bool(comparison.get("pair_internal_verdict_lift")),
        "pair_found_more_findings": bool(comparison.get("pair_found_more_findings")),
        "pair_found_more_low_or_worse": bool(comparison.get("pair_found_more_low_or_worse")),
        "row_failed_before_compare": bool(comparison.get("row_failed_before_compare")),
        "row_exit": comparison.get("row_exit"),
        "compare_missing": bool(comparison.get("compare_missing")),
        "solo_invoke_exit": solo.get("invoke_exit"),
        "pair_invoke_exit": pair.get("invoke_exit"),
        "solo_failure_reason": solo.get("invoke_failure_reason")
        or transcript_failure_reason(results_root, run_id, "solo"),
        "pair_failure_reason": pair.get("invoke_failure_reason")
        or transcript_failure_reason(results_root, run_id, "pair"),
        "solo_timed_out": bool(solo.get("timed_out")),
        "pair_timed_out": bool(pair.get("timed_out")),
        "pair_solo_wall_ratio": pair_ratio,
        "solo_mechanical": (solo.get("sub_verdicts") or {}).get("mechanical"),
        "pair_mechanical": (pair.get("sub_verdicts") or {}).get("mechanical"),
        "included_in_gate": gate_row.get("status") == "PASS",
        "gate_failures": gate_row.get("failures") or [],
    }
    row["classification"] = classify(row, row["included_in_gate"])
    return row


def fmt_ratio(value: Any) -> str:
    return f"{value:.2f}x" if isinstance(value, (int, float)) else "n/a"


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
            "| Fixture | Solo | Pair | Pair mode | Wall ratio | External lift | Internal lift | Included | Classification |",
            "|---|---|---|---|---:|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['fixture_id']} | {row['solo_verdict']} | {row['pair_verdict']} | "
            f"{str(row['pair_mode']).lower()} | {fmt_ratio(row.get('pair_solo_wall_ratio'))} | "
            f"{str(row['external_lift']).lower()} | {str(row['internal_lift']).lower()} | "
            f"{str(row['included_in_gate']).lower()} | {row['classification']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", default="benchmark/auto-resolve/results", type=Path)
    parser.add_argument("--run-id", action="append", required=True)
    parser.add_argument("--gate-json", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--verdict", required=True)
    parser.add_argument("--min-gate-rate", type=min_gate_rate)
    parser.add_argument("--max-trailing-non-gate", type=non_negative_int)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    args = parser.parse_args()

    gate_rows_by_id = load_gate_rows(args.gate_json)
    rows = [build_row(args.results_root, run_id, gate_rows_by_id) for run_id in args.run_id]
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
