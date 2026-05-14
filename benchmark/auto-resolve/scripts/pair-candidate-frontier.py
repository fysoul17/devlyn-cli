#!/usr/bin/env python3
"""Report active pair-candidate fixture frontier.

This is a spending guard for solo<pair work. It answers three questions before
new provider calls:
  - which active fixtures are already rejected by measured headroom/design,
  - which active fixtures remain pair-candidate eligible,
  - which eligible fixtures already have passing full-pipeline pair evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import subprocess
import sys
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import (
    all_known_pair_trigger_reasons,
    best_pair_evidence,
    has_canonical_pair_trigger_reason,
    has_known_pair_trigger_reason,
    is_strict_number,
    loads_strict_json_object,
    normalize_pair_evidence_row,
)


def fixture_short(name: str) -> str:
    return name.split("-", 1)[0] if "-" in name else name


def sort_fixture_key(name: str) -> tuple[int, str]:
    short = fixture_short(name)
    match = re.fullmatch(r"F(\d+)", short)
    return (int(match.group(1)) if match else 10_000, name)


def active_fixtures(fixtures_root: pathlib.Path) -> list[str]:
    if not fixtures_root.is_dir():
        raise ValueError(f"fixtures root missing: {fixtures_root}")
    return sorted(
        [
            path.name
            for path in fixtures_root.iterdir()
            if path.is_dir() and re.fullmatch(r"F\d+-.+", path.name)
        ],
        key=sort_fixture_key,
    )


def registry_short_ids(registry: pathlib.Path) -> set[str]:
    if not registry.is_file():
        raise ValueError(f"rejected fixture registry missing: {registry}")
    rejected: set[str] = set()
    for line in registry.read_text().splitlines():
        match = re.match(r"\s*([FS]\d+)-\*\|([FS]\d+)\)", line)
        if match and match.group(1) == match.group(2):
            rejected.add(match.group(1))
    if not rejected:
        raise ValueError(f"rejected fixture registry has no fixture entries: {registry}")
    return rejected


def rejected_reason(registry: pathlib.Path, fixture: str) -> str | None:
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; rejected_pair_fixture_reason "$2"',
            "bash",
            str(registry),
            fixture,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout.strip()
    return None


def load_json_object(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        raise ValueError(f"pair evidence artifact malformed: {path}") from None
    return data


def pair_gate_rows(path: pathlib.Path, gate: dict[str, Any]) -> list[dict[str, Any]]:
    rows = gate.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"pair evidence artifact rows malformed: {path}")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"pair evidence artifact rows malformed: {path}")
    return rows


def pair_result_trigger_reasons(
    results_root: pathlib.Path,
    *,
    run_id: str,
    fixture: str,
    pair_arm: str,
) -> list[str]:
    path = results_root / run_id / fixture / pair_arm / "result.json"
    try:
        result = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    trigger = result.get("pair_trigger")
    if not isinstance(trigger, dict):
        return []
    reasons = trigger.get("reasons")
    if not (
        isinstance(reasons, list)
        and reasons
        and all(isinstance(reason, str) for reason in reasons)
        and has_known_pair_trigger_reason(reasons)
        and all_known_pair_trigger_reasons(reasons)
        and has_canonical_pair_trigger_reason(reasons)
    ):
        return []
    return reasons


def passing_pair_evidence(
    results_root: pathlib.Path,
    *,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float,
) -> dict[str, list[dict[str, Any]]]:
    evidence: dict[str, list[dict[str, Any]]] = {}
    if not results_root.is_dir():
        return evidence
    for gate_path in sorted(results_root.glob("*/full-pipeline-pair-gate.json")):
        gate = load_json_object(gate_path)
        if gate.get("verdict") != "PASS":
            continue
        run_id = str(gate.get("run_id") or gate_path.parent.name)
        pair_arm = gate.get("pair_arm")
        for row in pair_gate_rows(gate_path, gate):
            if row.get("status") != "PASS":
                continue
            fixture = row.get("fixture")
            if not isinstance(fixture, str):
                continue
            candidate_row = row
            if row.get("pair_trigger_reasons") is None and isinstance(pair_arm, str):
                reasons = pair_result_trigger_reasons(
                    results_root,
                    run_id=run_id,
                    fixture=fixture,
                    pair_arm=pair_arm,
                )
                if reasons:
                    candidate_row = dict(row)
                    candidate_row["pair_trigger_reasons"] = reasons
                    candidate_row["pair_trigger_has_canonical_reason"] = True
            evidence_row = normalize_pair_evidence_row(
                fixture=fixture,
                run_id=run_id,
                pair_arm=pair_arm,
                row=candidate_row,
            )
            if evidence_row is None:
                continue
            pair_margin = evidence_row["pair_margin"]
            wall_ratio = evidence_row["pair_solo_wall_ratio"]
            if pair_margin < min_pair_margin or wall_ratio > max_pair_solo_wall_ratio:
                continue
            evidence.setdefault(fixture, []).append(evidence_row)
    return evidence


def build_report(
    *,
    fixtures_root: pathlib.Path,
    registry: pathlib.Path,
    results_root: pathlib.Path,
    min_pair_margin: int = 5,
    max_pair_solo_wall_ratio: float = 3.0,
) -> dict[str, Any]:
    fixtures = active_fixtures(fixtures_root)
    rejected_short = registry_short_ids(registry)
    evidence_by_fixture = passing_pair_evidence(
        results_root,
        min_pair_margin=min_pair_margin,
        max_pair_solo_wall_ratio=max_pair_solo_wall_ratio,
    )

    rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        reason = rejected_reason(registry, fixture) if fixture_short(fixture) in rejected_short else None
        evidence = evidence_by_fixture.get(fixture, [])
        if reason:
            status = "rejected"
        elif evidence:
            status = "pair_evidence_passed"
        else:
            status = "candidate_unmeasured"
        rows.append(
            {
                "fixture": fixture,
                "short_id": fixture_short(fixture),
                "status": status,
                "rejected_reason": reason,
                "passing_pair_evidence": evidence,
            }
        )

    rejected_total = sum(1 for row in rows if row["status"] == "rejected")
    candidate_total = sum(1 for row in rows if row["status"] != "rejected")
    pair_evidence_total = sum(
        1 for row in rows if row["status"] == "pair_evidence_passed"
    )
    unmeasured_candidate_total = sum(
        1 for row in rows if row["status"] == "candidate_unmeasured"
    )
    best_pairs = [
        best
        for row in rows
        if row["status"] == "pair_evidence_passed"
        for best in [best_pair_evidence(row["passing_pair_evidence"])]
        if best is not None
    ]
    pair_margins = [
        item["pair_margin"]
        for item in best_pairs
        if isinstance(item.get("pair_margin"), int)
    ]
    wall_ratios = [
        item["pair_solo_wall_ratio"]
        for item in best_pairs
        if is_strict_number(item.get("pair_solo_wall_ratio"))
    ]

    return {
        "verdict": "PASS" if unmeasured_candidate_total == 0 else "FAIL",
        "min_pair_margin": min_pair_margin,
        "max_pair_solo_wall_ratio": max_pair_solo_wall_ratio,
        "fixtures_total": len(rows),
        "rejected_total": rejected_total,
        "candidate_total": candidate_total,
        "pair_evidence_total": pair_evidence_total,
        "unmeasured_candidate_total": unmeasured_candidate_total,
        "rejected_count": rejected_total,
        "candidate_count": candidate_total,
        "pair_evidence_count": pair_evidence_total,
        "unmeasured_count": unmeasured_candidate_total,
        "pair_margin_avg": average(pair_margins),
        "pair_margin_min": min(pair_margins) if pair_margins else None,
        "pair_solo_wall_ratio_avg": average(wall_ratios),
        "pair_solo_wall_ratio_max": round(max(wall_ratios), 2) if wall_ratios else None,
        "rows": rows,
    }


def write_markdown(path: pathlib.Path, report: dict[str, Any]) -> None:
    lines = [
        "# Pair Candidate Frontier",
        "",
        f"Active fixtures: {report['fixtures_total']}",
        f"Verdict: {report['verdict']}",
        f"Rejected fixtures: {report['rejected_total']}",
        f"Candidate fixtures: {report['candidate_total']}",
        f"Candidates with passing pair evidence: {report['pair_evidence_total']}",
        f"Unmeasured candidates: {report['unmeasured_candidate_total']}",
        f"Minimum pair margin required: {format_margin(report.get('min_pair_margin'))}",
        f"Maximum pair/solo wall ratio allowed: {format_wall_ratio(report.get('max_pair_solo_wall_ratio'))}",
        f"Average pair margin: {format_decimal_margin(report.get('pair_margin_avg'))}",
        f"Minimum pair margin: {format_margin(report.get('pair_margin_min'))}",
        f"Average pair/solo wall ratio: {format_wall_ratio(report.get('pair_solo_wall_ratio_avg'))}",
        f"Maximum pair/solo wall ratio: {format_wall_ratio(report.get('pair_solo_wall_ratio_max'))}",
        "",
        "| Fixture | Status | Verdict | Evidence | Pair arm | Triggers | Hypothesis trigger | Bare | Solo_claude | Pair | Margin | Wall ratio | Rejected reason |",
        "|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        evidence = row["passing_pair_evidence"]
        best = best_pair_evidence(evidence)
        evidence_text = best.get("run_id", "") if best else ""
        pair_arm = best.get("pair_arm", "") if best else ""
        triggers = format_trigger_reasons(best.get("pair_trigger_reasons")) if best else ""
        lines.append(
            f"| {row['fixture']} | {row['status']} | {row['status']} | {evidence_text} | {pair_arm} | {triggers} | "
            f"{format_bool(best.get('pair_trigger_has_hypothesis_reason') if best else None)} | "
            f"{format_number(best.get('bare_score') if best else None)} | "
            f"{format_number(best.get('solo_score') if best else None)} | "
            f"{format_number(best.get('pair_score') if best else None)} | "
            f"{format_margin(best.get('pair_margin') if best else None)} | "
            f"{format_wall_ratio(best.get('pair_solo_wall_ratio') if best else None)} | "
            f"{row.get('rejected_reason') or ''} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf8")


def average(values: list[int | float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def format_number(value: Any) -> str:
    return str(value) if isinstance(value, int) else ""


def format_decimal_margin(value: Any) -> str:
    return f"{value:+.2f}" if isinstance(value, (int, float)) else ""


def format_margin(value: Any) -> str:
    return f"{value:+d}" if isinstance(value, int) else ""


def format_wall_ratio(value: Any) -> str:
    return f"{value:.2f}x" if is_strict_number(value) else ""


def format_trigger_reasons(value: Any) -> str:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return ""
    return ",".join(value)


def format_bool(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else ""


def print_summary(report: dict[str, Any]) -> None:
    print(
        "fixtures={fixtures_total} rejected={rejected_total} "
        "candidates={candidate_total} pair_evidence={pair_evidence_total} "
        "unmeasured={unmeasured_candidate_total} verdict={verdict}".format(**report)
    )
    if report.get("pair_evidence_total"):
        print(
            "pair_margin_avg={avg} pair_margin_min={min_margin} "
            "wall_avg={wall_avg} wall_max={wall_max}".format(
                avg=format_decimal_margin(report.get("pair_margin_avg")),
                min_margin=format_margin(report.get("pair_margin_min")),
                wall_avg=format_wall_ratio(report.get("pair_solo_wall_ratio_avg")),
                wall_max=format_wall_ratio(report.get("pair_solo_wall_ratio_max")),
            )
        )
    for row in report["rows"]:
        if row["status"] != "pair_evidence_passed":
            continue
        best = best_pair_evidence(row["passing_pair_evidence"])
        if not best:
            continue
        print(
            "{fixture}: bare={bare} solo_claude={solo} pair={pair} arm={arm} margin={margin} "
            "wall={wall} run={run} verdict=pair_evidence_passed triggers={triggers} "
            "hypothesis_trigger={hypothesis_trigger}".format(
                fixture=row["fixture"],
                bare=format_number(best.get("bare_score")),
                solo=format_number(best.get("solo_score")),
                pair=format_number(best.get("pair_score")),
                arm=best.get("pair_arm") or "",
                margin=format_margin(best.get("pair_margin")),
                wall=format_wall_ratio(best.get("pair_solo_wall_ratio")),
                run=best.get("run_id") or "",
                triggers=format_trigger_reasons(best.get("pair_trigger_reasons")),
                hypothesis_trigger=format_bool(best.get("pair_trigger_has_hypothesis_reason")),
            )
        )


def print_final_verdict(report: dict[str, Any]) -> None:
    if report.get("verdict") == "PASS":
        print("PASS pair-candidate-frontier", flush=True)
    else:
        print("FAIL pair-candidate-frontier", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures-root",
        type=pathlib.Path,
        default=pathlib.Path("benchmark/auto-resolve/fixtures"),
    )
    parser.add_argument(
        "--registry",
        type=pathlib.Path,
        default=pathlib.Path(__file__).with_name("pair-rejected-fixtures.sh"),
    )
    parser.add_argument(
        "--results-root",
        type=pathlib.Path,
        default=pathlib.Path("benchmark/auto-resolve/results"),
    )
    parser.add_argument("--out-json", type=pathlib.Path)
    parser.add_argument("--out-md", type=pathlib.Path)
    parser.add_argument(
        "--fail-on-unmeasured",
        action="store_true",
        help="exit 1 when active candidate_unmeasured fixtures remain",
    )
    parser.add_argument(
        "--min-pair-margin",
        type=int,
        default=5,
        help="minimum pair-over-solo margin required to count passing pair evidence",
    )
    parser.add_argument(
        "--max-pair-solo-wall-ratio",
        type=float,
        default=3.0,
        help="maximum pair/solo wall-time ratio allowed to count passing pair evidence",
    )
    args = parser.parse_args()
    if args.min_pair_margin < 1:
        print("error: --min-pair-margin must be >= 1", file=sys.stderr)
        return 2
    if not math.isfinite(args.max_pair_solo_wall_ratio) or args.max_pair_solo_wall_ratio <= 0:
        print("error: --max-pair-solo-wall-ratio must be finite and > 0", file=sys.stderr)
        return 2

    try:
        report = build_report(
            fixtures_root=args.fixtures_root,
            registry=args.registry,
            results_root=args.results_root,
            min_pair_margin=args.min_pair_margin,
            max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(args.out_md, report)
    if not args.out_json and not args.out_md:
        print(json.dumps(report, indent=2))
    else:
        print_summary(report)
        print_final_verdict(report)
    if args.fail_on_unmeasured and report["unmeasured_candidate_total"] > 0:
        unmeasured = [
            row["fixture"]
            for row in report["rows"]
            if row["status"] == "candidate_unmeasured"
        ]
        print(
            "unmeasured candidate fixture(s): " + ", ".join(unmeasured),
            file=sys.stderr,
        )
        if not args.out_json and not args.out_md:
            print("FAIL pair-candidate-frontier", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
