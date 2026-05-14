#!/usr/bin/env python3
"""Composite audit for pair-evidence readiness.

This is the release/handoff guard for solo<pair benchmark evidence. It runs:
  1. pair-candidate-frontier.py --fail-on-unmeasured
  2. audit-headroom-rejections.py

Both checks are provider-free and operate only on fixtures, the rejected
registry, and local gate summary artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import sys
import tempfile

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import (
    best_pair_evidence,
    has_historical_pair_trigger_reason,
    is_historical_pair_trigger_reason,
    is_strict_int,
    is_strict_number,
    loads_strict_json_object,
)


FRONTIER_SUMMARY_KEYS = [
    "verdict",
    "min_pair_margin",
    "max_pair_solo_wall_ratio",
    "fixtures_total",
    "rejected_count",
    "candidate_count",
    "pair_evidence_count",
    "unmeasured_count",
    "pair_margin_avg",
    "pair_margin_min",
    "pair_solo_wall_ratio_avg",
    "pair_solo_wall_ratio_max",
]
def run_check(
    name: str,
    args: list[str],
    *,
    stdout_path: pathlib.Path | None = None,
    stderr_path: pathlib.Path | None = None,
) -> int:
    print(f"[audit] {name}", flush=True)
    proc = subprocess.run(args, text=True, capture_output=True)
    if stdout_path is not None:
        stdout_path.write_text(proc.stdout, encoding="utf8")
    if stderr_path is not None:
        stderr_path.write_text(proc.stderr, encoding="utf8")
    if proc.stdout:
        print(proc.stdout, end="", flush=True)
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr, flush=True)
    if proc.returncode == 0:
        print(f"[audit] {name}: PASS", flush=True)
    else:
        print(f"[audit] {name}: FAIL", file=sys.stderr, flush=True)
    return proc.returncode


def write_audit_report(
    *,
    out_dir: pathlib.Path,
    frontier_status: int,
    headroom_status: int,
    min_pair_evidence: int,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float,
    frontier_report_status: int,
    frontier_stdout_status: int,
    headroom_report_status: int,
    pair_evidence_status: int,
    pair_evidence_quality_status: int,
    pair_trigger_reason_status: int,
    pair_evidence_hypothesis_status: int,
    pair_evidence_hypothesis_trigger_status: int,
    require_hypothesis_trigger: bool,
    fixtures_root: pathlib.Path,
) -> None:
    frontier_summary = load_summary(out_dir / "frontier.json", FRONTIER_SUMMARY_KEYS)
    pair_evidence_rows = load_pair_evidence_rows(out_dir / "frontier.json")
    pair_evidence_count = frontier_summary.get("pair_evidence_count")
    pair_margins = [
        row["pair_margin"]
        for row in pair_evidence_rows
        if is_strict_int(row.get("pair_margin"))
    ]
    wall_ratios = [
        row["pair_solo_wall_ratio"]
        for row in pair_evidence_rows
        if is_strict_number(row.get("pair_solo_wall_ratio"))
    ]
    trigger_reason_rows = [
        row
        for row in pair_evidence_rows
        if isinstance(row.get("pair_trigger_reasons"), list)
    ]
    canonical_trigger_rows = [
        row
        for row in trigger_reason_rows
        if row.get("pair_trigger_has_canonical_reason") is True
    ]
    historical_alias_trigger_rows = [
        row
        for row in trigger_reason_rows
        if has_historical_pair_trigger_reason(row["pair_trigger_reasons"])
    ]
    historical_alias_details = pair_trigger_historical_alias_details(
        historical_alias_trigger_rows,
    )
    hypothesis_rows = pair_evidence_hypothesis_rows(
        out_dir / "frontier.json",
        fixtures_root,
    )
    hypothesis_passing_rows = [
        row for row in hypothesis_rows if row.get("has_actionable_hypothesis") is True
    ]
    hypothesis_trigger_rows = pair_evidence_hypothesis_trigger_rows(
        out_dir / "frontier.json",
        fixtures_root,
    )
    hypothesis_trigger_matched_rows = [
        row
        for row in hypothesis_trigger_rows
        if row.get("has_actionable_hypothesis") is True
        and row.get("has_hypothesis_trigger") is True
    ]
    hypothesis_trigger_gap_details = pair_evidence_hypothesis_trigger_gap_details(
        hypothesis_trigger_rows,
    )
    frontier_stdout_metrics = load_frontier_stdout_metrics(
        out_dir / "frontier.json",
        out_dir / "frontier.stdout",
    )
    headroom_audit_summary = load_headroom_audit_summary(
        out_dir / "headroom-audit.json",
    )
    report = {
        "verdict": (
            "PASS"
            if (
                frontier_status == 0
                and headroom_status == 0
                and frontier_report_status == 0
                and frontier_stdout_status == 0
                and headroom_report_status == 0
                and pair_evidence_status == 0
                and pair_evidence_quality_status == 0
                and pair_trigger_reason_status == 0
                and pair_evidence_hypothesis_status == 0
                and pair_evidence_hypothesis_trigger_status == 0
            )
            else "FAIL"
        ),
        "min_pair_evidence": min_pair_evidence,
        "min_pair_margin": min_pair_margin,
        "max_pair_solo_wall_ratio": max_pair_solo_wall_ratio,
        "frontier_summary": frontier_summary,
        "pair_evidence_rows": pair_evidence_rows,
        "artifacts": {
            "frontier_json": "frontier.json",
            "frontier_stdout": "frontier.stdout",
            "frontier_stderr": "frontier.stderr",
            "headroom_audit_json": "headroom-audit.json",
            "headroom_rejections_stdout": "headroom-rejections.stdout",
            "headroom_rejections_stderr": "headroom-rejections.stderr",
            "audit_json": "audit.json",
        },
        "checks": {
            "frontier": {
                "status": "PASS" if frontier_status == 0 else "FAIL",
                "exit_code": frontier_status,
                "report": str(out_dir / "frontier.json"),
            },
            "headroom_rejections": {
                "status": (
                    "PASS"
                    if headroom_status == 0 and headroom_report_status == 0
                    else "FAIL"
                ),
                "exit_code": headroom_status,
                "report_check_exit_code": headroom_report_status,
                "report": str(out_dir / "headroom-audit.json"),
                **headroom_audit_summary,
            },
            "frontier_report": {
                "status": "PASS" if frontier_report_status == 0 else "FAIL",
                "exit_code": frontier_report_status,
                "verdict": frontier_summary.get("verdict"),
                "unmeasured_count": frontier_summary.get("unmeasured_count"),
            },
            "frontier_stdout": {
                "status": "PASS" if frontier_stdout_status == 0 else "FAIL",
                "exit_code": frontier_stdout_status,
                "report": str(out_dir / "frontier.stdout"),
                **frontier_stdout_metrics,
            },
            "min_pair_evidence": {
                "status": "PASS" if pair_evidence_status == 0 else "FAIL",
                "exit_code": pair_evidence_status,
                "required": min_pair_evidence,
                "actual": pair_evidence_count,
                "actual_rows": len(pair_evidence_rows),
                "rows_match_count": (
                    is_strict_int(pair_evidence_count)
                    and len(pair_evidence_rows) == pair_evidence_count
                ),
            },
            "pair_evidence_quality": {
                "status": "PASS" if pair_evidence_quality_status == 0 else "FAIL",
                "exit_code": pair_evidence_quality_status,
                "min_pair_margin_required": min_pair_margin,
                "min_pair_margin_actual": min(pair_margins) if pair_margins else None,
                "max_pair_solo_wall_ratio_allowed": max_pair_solo_wall_ratio,
                "max_pair_solo_wall_ratio_actual": (
                    round(max(wall_ratios), 2) if wall_ratios else None
                ),
                "summary_min_pair_margin": frontier_summary.get("pair_margin_min"),
                "summary_max_pair_solo_wall_ratio": frontier_summary.get("pair_solo_wall_ratio_max"),
            },
            "pair_trigger_reasons": {
                "status": "PASS" if pair_trigger_reason_status == 0 else "FAIL",
                "exit_code": pair_trigger_reason_status,
                "summary_pair_evidence_count": pair_evidence_count,
                "canonical_rows": len(canonical_trigger_rows),
                "historical_alias_rows": len(historical_alias_trigger_rows),
                "historical_alias_details": historical_alias_details,
                "exposed_rows": len(trigger_reason_rows),
                "total_rows": len(pair_evidence_rows),
                "rows_match_count": (
                    is_strict_int(pair_evidence_count)
                    and len(pair_evidence_rows) == pair_evidence_count
                ),
            },
            "pair_evidence_hypotheses": {
                "status": "PASS" if pair_evidence_hypothesis_status == 0 else "FAIL",
                "exit_code": pair_evidence_hypothesis_status,
                "documented_rows": len(hypothesis_passing_rows),
                "total_rows": len(pair_evidence_rows),
                "rows": hypothesis_rows,
            },
            "pair_evidence_hypothesis_triggers": {
                "status": (
                    "PASS"
                    if len(hypothesis_trigger_matched_rows) == len(hypothesis_passing_rows)
                    else ("FAIL" if require_hypothesis_trigger else "WARN")
                ),
                "exit_code": pair_evidence_hypothesis_trigger_status,
                "required": require_hypothesis_trigger,
                "matched_rows": len(hypothesis_trigger_matched_rows),
                "documented_rows": len(hypothesis_passing_rows),
                "total_rows": len(pair_evidence_rows),
                "gap_details": hypothesis_trigger_gap_details,
                "rows": hypothesis_trigger_rows,
            },
        },
    }
    (out_dir / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")


def load_summary(path: pathlib.Path, keys: list[str]) -> dict[str, object]:
    try:
        data = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return {key: data.get(key) for key in keys if key in data}


def pair_trigger_historical_alias_details(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "fixture": row["fixture"],
            "aliases": [
                reason
                for reason in row["pair_trigger_reasons"]
                if isinstance(reason, str)
                and is_historical_pair_trigger_reason(reason)
            ],
        }
        for row in rows
        if isinstance(row.get("pair_trigger_reasons"), list)
    ]


def pair_evidence_hypothesis_trigger_gap_details(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "fixture": row["fixture"],
            "pair_trigger_reasons": [
                reason
                for reason in row["pair_trigger_reasons"]
                if isinstance(reason, str)
            ],
        }
        for row in rows
        if row.get("has_actionable_hypothesis") is True
        and row.get("has_hypothesis_trigger") is not True
        and isinstance(row.get("pair_trigger_reasons"), list)
    ]


def load_headroom_audit_summary(path: pathlib.Path) -> dict[str, object]:
    try:
        data = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "verdict": None,
            "unrecorded_failure_count": None,
            "unsupported_registry_rejection_count": None,
        }
    unrecorded = data.get("unrecorded_failures")
    unsupported = data.get("unsupported_registry_rejections")
    return {
        "verdict": data.get("verdict"),
        "unrecorded_failure_count": (
            len(unrecorded) if isinstance(unrecorded, list) else None
        ),
        "unsupported_registry_rejection_count": (
            len(unsupported) if isinstance(unsupported, list) else None
        ),
    }


def check_headroom_audit_report(headroom_json: pathlib.Path) -> int:
    summary = load_headroom_audit_summary(headroom_json)
    verdict = summary.get("verdict")
    unrecorded_count = summary.get("unrecorded_failure_count")
    unsupported_count = summary.get("unsupported_registry_rejection_count")
    if verdict != "PASS":
        print(f"headroom audit verdict {verdict!r} is not PASS", file=sys.stderr)
        return 1
    if not is_strict_int(unrecorded_count):
        print(
            "headroom audit unrecorded failure count missing or malformed",
            file=sys.stderr,
        )
        return 1
    if not is_strict_int(unsupported_count):
        print(
            "headroom audit unsupported registry rejection count missing or malformed",
            file=sys.stderr,
        )
        return 1
    if unrecorded_count != 0:
        print(
            f"headroom audit has {unrecorded_count} unrecorded failure(s)",
            file=sys.stderr,
        )
        return 1
    if unsupported_count != 0:
        print(
            f"headroom audit has {unsupported_count} unsupported registry rejection(s)",
            file=sys.stderr,
        )
        return 1
    return 0


def print_headroom_rejections_summary(
    headroom_json: pathlib.Path,
    *,
    status: int,
) -> None:
    summary = load_headroom_audit_summary(headroom_json)
    print(
        "headroom_rejections={status} verdict={verdict} "
        "unrecorded={unrecorded} unsupported={unsupported}".format(
            status="PASS" if status == 0 else "FAIL",
            verdict=summary.get("verdict") or "MISSING",
            unrecorded=format_count(summary.get("unrecorded_failure_count")),
            unsupported=format_count(
                summary.get("unsupported_registry_rejection_count")
            ),
        ),
        flush=True,
    )


def load_frontier_stdout_metrics(
    frontier_json: pathlib.Path,
    frontier_stdout: pathlib.Path,
) -> dict[str, object]:
    expected_rows = len(load_pair_evidence_rows(frontier_json))
    try:
        stdout = frontier_stdout.read_text(encoding="utf8")
    except OSError:
        return {
            "summary_rows": None,
            "aggregate_rows": None,
            "final_verdict_rows": None,
            "expected_rows": expected_rows,
            "stdout_rows": None,
            "trigger_rows": None,
            "hypothesis_trigger_rows": None,
            "rows_match_count": False,
            "trigger_rows_match_count": False,
            "hypothesis_trigger_rows_match_count": False,
        }
    summary = load_summary(
        frontier_json,
        [
            "verdict",
            "fixtures_total",
            "rejected_count",
            "candidate_count",
            "pair_evidence_count",
            "unmeasured_count",
            "pair_margin_avg",
            "pair_margin_min",
            "pair_solo_wall_ratio_avg",
            "pair_solo_wall_ratio_max",
        ],
    )
    summary_rows = None
    aggregate_rows = None
    final_verdict_rows = None
    if all(key in summary for key in [
        "verdict",
        "fixtures_total",
        "rejected_count",
        "candidate_count",
        "pair_evidence_count",
        "unmeasured_count",
    ]):
        expected_summary = (
            "fixtures={fixtures_total} rejected={rejected_count} candidates={candidate_count} "
            "pair_evidence={pair_evidence_count} unmeasured={unmeasured_count} verdict={verdict}"
        ).format(**summary)
        summary_rows = stdout.splitlines().count(expected_summary)
        if summary["verdict"] in {"PASS", "FAIL"}:
            final_verdict_rows = stdout.splitlines().count(
                f"{summary['verdict']} pair-candidate-frontier"
            )
    if all(key in summary for key in [
        "pair_margin_avg",
        "pair_margin_min",
        "pair_solo_wall_ratio_avg",
        "pair_solo_wall_ratio_max",
    ]):
        expected_aggregate = (
            "pair_margin_avg={avg} pair_margin_min={min_margin} "
            "wall_avg={wall_avg} wall_max={wall_max}"
        ).format(
            avg=format_decimal_margin(summary.get("pair_margin_avg")),
            min_margin=format_margin(summary.get("pair_margin_min")),
            wall_avg=format_wall_ratio(summary.get("pair_solo_wall_ratio_avg")),
            wall_max=format_wall_ratio(summary.get("pair_solo_wall_ratio_max")),
        )
        aggregate_rows = stdout.splitlines().count(expected_aggregate)
    stdout_rows = len(
        [
            line
            for line in stdout.splitlines()
            if "verdict=pair_evidence_passed" in line
        ]
    )
    trigger_rows = len(
        [
            line
            for line in stdout.splitlines()
            if "verdict=pair_evidence_passed" in line and " triggers=" in line
        ]
    )
    hypothesis_trigger_rows = len(
        [
            line
            for line in stdout.splitlines()
            if "verdict=pair_evidence_passed" in line and " hypothesis_trigger=" in line
        ]
    )
    return {
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "final_verdict_rows": final_verdict_rows,
        "expected_rows": expected_rows,
        "stdout_rows": stdout_rows,
        "trigger_rows": trigger_rows,
        "hypothesis_trigger_rows": hypothesis_trigger_rows,
        "rows_match_count": stdout_rows == expected_rows,
        "trigger_rows_match_count": trigger_rows == expected_rows,
        "hypothesis_trigger_rows_match_count": hypothesis_trigger_rows == expected_rows,
    }


def load_pair_evidence_rows(path: pathlib.Path) -> list[dict[str, object]]:
    try:
        data = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    rows = data.get("rows")
    if not isinstance(rows, list):
        return []
    evidence_rows: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "pair_evidence_passed":
            continue
        fixture = row.get("fixture")
        evidence = row.get("passing_pair_evidence")
        if not isinstance(fixture, str) or not isinstance(evidence, list):
            continue
        best = best_pair_evidence(evidence)
        if best is not None:
            evidence_rows.append({
                "fixture": fixture,
                "verdict": "pair_evidence_passed",
                **best,
            })
    return evidence_rows


def check_min_pair_evidence(frontier_json: pathlib.Path, minimum: int) -> int:
    summary = load_summary(frontier_json, ["pair_evidence_count"])
    count = summary.get("pair_evidence_count")
    if not is_strict_int(count):
        print("pair evidence count missing or malformed from frontier report", file=sys.stderr)
        return 1
    if count < minimum:
        print(
            f"pair evidence count {count} below required minimum {minimum}",
            file=sys.stderr,
        )
        return 1
    rows = load_pair_evidence_rows(frontier_json)
    if len(rows) != count:
        print(
            f"pair evidence rows {len(rows)} do not match summary count {count}",
            file=sys.stderr,
        )
        return 1
    return 0


def check_pair_evidence_quality(
    frontier_json: pathlib.Path,
    *,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float,
) -> int:
    rows = load_pair_evidence_rows(frontier_json)
    if not rows:
        print("pair evidence quality check has no complete rows", file=sys.stderr)
        return 1
    low_margin = [
        row["fixture"]
        for row in rows
        if row["pair_margin"] < min_pair_margin
    ]
    if low_margin:
        print(
            "pair evidence margin below minimum for fixture(s): "
            + ", ".join(low_margin),
            file=sys.stderr,
        )
        return 1
    high_wall = [
        row["fixture"]
        for row in rows
        if row["pair_solo_wall_ratio"] > max_pair_solo_wall_ratio
    ]
    if high_wall:
        print(
            "pair evidence wall ratio above maximum for fixture(s): "
            + ", ".join(high_wall),
            file=sys.stderr,
        )
        return 1
    summary = load_summary(
        frontier_json,
        ["pair_margin_min", "pair_solo_wall_ratio_max"],
    )
    actual_min_margin = min(row["pair_margin"] for row in rows)
    actual_max_wall = round(max(row["pair_solo_wall_ratio"] for row in rows), 2)
    if summary.get("pair_margin_min") != actual_min_margin:
        print("frontier pair_margin_min does not match pair evidence rows", file=sys.stderr)
        return 1
    if summary.get("pair_solo_wall_ratio_max") != actual_max_wall:
        print(
            "frontier pair_solo_wall_ratio_max does not match pair evidence rows",
            file=sys.stderr,
        )
        return 1
    return 0


def print_pair_evidence_quality(
    frontier_json: pathlib.Path,
    *,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float,
    status: int,
) -> None:
    rows = load_pair_evidence_rows(frontier_json)
    pair_margins = [
        row["pair_margin"]
        for row in rows
        if is_strict_int(row.get("pair_margin"))
    ]
    wall_ratios = [
        row["pair_solo_wall_ratio"]
        for row in rows
        if is_strict_number(row.get("pair_solo_wall_ratio"))
    ]
    print(
        "pair_evidence_quality={status} min_pair_margin_actual={actual_margin} "
        "min_pair_margin_required={required_margin} max_wall_actual={actual_wall} "
        "max_wall_allowed={allowed_wall}".format(
            status="PASS" if status == 0 else "FAIL",
            actual_margin=format_margin(min(pair_margins) if pair_margins else None),
            required_margin=format_margin(min_pair_margin),
            actual_wall=format_wall_ratio(max(wall_ratios) if wall_ratios else None),
            allowed_wall=format_wall_ratio(max_pair_solo_wall_ratio),
        ),
        flush=True,
    )


def check_pair_trigger_reasons(frontier_json: pathlib.Path) -> int:
    rows = load_pair_evidence_rows(frontier_json)
    summary = load_summary(frontier_json, ["pair_evidence_count"])
    count = summary.get("pair_evidence_count")
    if not is_strict_int(count):
        print("pair trigger reason count missing or malformed from frontier report", file=sys.stderr)
        return 1
    if len(rows) != count:
        print(
            f"pair trigger reason rows {len(rows)} do not match summary count {count}",
            file=sys.stderr,
        )
        return 1
    missing = [
        row["fixture"]
        for row in rows
        if not isinstance(row.get("pair_trigger_reasons"), list)
    ]
    malformed = [
        row["fixture"]
        for row in rows
        if isinstance(row.get("pair_trigger_reasons"), list)
        and row.get("pair_trigger_has_canonical_reason") is not True
    ]
    if missing:
        print(
            "pair trigger reasons missing for fixture(s): "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 1
    if malformed:
        print(
            "pair trigger reasons missing canonical trigger for fixture(s): "
            + ", ".join(malformed),
            file=sys.stderr,
        )
        return 1
    return 0


def print_pair_trigger_reasons_summary(
    frontier_json: pathlib.Path,
    *,
    status: int,
) -> None:
    rows = load_pair_evidence_rows(frontier_json)
    summary = load_summary(frontier_json, ["pair_evidence_count"])
    count = summary.get("pair_evidence_count")
    rows_match = is_strict_int(count) and len(rows) == count
    exposed = [
        row
        for row in rows
        if isinstance(row.get("pair_trigger_reasons"), list)
    ]
    canonical = [
        row
        for row in exposed
        if row.get("pair_trigger_has_canonical_reason") is True
    ]
    historical_alias = [
        row
        for row in exposed
        if has_historical_pair_trigger_reason(row["pair_trigger_reasons"])
    ]
    historical_alias_details = pair_trigger_historical_alias_details(historical_alias)
    print(
        "pair_trigger_reasons={status} canonical={canonical} historical_alias={historical_alias} "
        "exposed={exposed} total={total} summary={summary} rows_match={rows_match}".format(
            status="PASS" if status == 0 else "FAIL",
            canonical=len(canonical),
            historical_alias=len(historical_alias),
            exposed=len(exposed),
            total=len(rows),
            summary=format_count(count),
            rows_match=str(rows_match).lower(),
        ),
        flush=True,
    )
    if historical_alias_details:
        details = [
            f"{row['fixture']}={','.join(row['aliases'])}"
            for row in historical_alias_details
        ]
        print(
            "pair_trigger_historical_aliases=" + ";".join(details),
            flush=True,
        )


def fixture_has_actionable_hypothesis(fixtures_root: pathlib.Path, fixture: str) -> bool:
    checker = SCRIPT_DIR / "solo-headroom-hypothesis.py"
    fixture_dir = fixtures_root / fixture
    proc = subprocess.run(
        [
            sys.executable,
            str(checker),
            "--expected-json",
            str(fixture_dir / "expected.json"),
            str(fixture_dir / "spec.md"),
        ],
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0


def pair_evidence_hypothesis_rows(
    frontier_json: pathlib.Path,
    fixtures_root: pathlib.Path,
) -> list[dict[str, object]]:
    rows = load_pair_evidence_rows(frontier_json)
    return [
        {
            "fixture": row["fixture"],
            "has_actionable_hypothesis": fixture_has_actionable_hypothesis(
                fixtures_root,
                str(row["fixture"]),
            ),
        }
        for row in rows
    ]


def pair_evidence_hypothesis_trigger_rows(
    frontier_json: pathlib.Path,
    fixtures_root: pathlib.Path,
) -> list[dict[str, object]]:
    rows = load_pair_evidence_rows(frontier_json)
    result: list[dict[str, object]] = []
    for row in rows:
        reasons = row.get("pair_trigger_reasons")
        has_actionable = fixture_has_actionable_hypothesis(
            fixtures_root,
            str(row["fixture"]),
        )
        has_hypothesis_trigger = (
            isinstance(reasons, list)
            and "spec.solo_headroom_hypothesis" in reasons
        )
        result.append(
            {
                "fixture": row["fixture"],
                "has_actionable_hypothesis": has_actionable,
                "has_hypothesis_trigger": has_hypothesis_trigger,
                "pair_trigger_reasons": reasons if isinstance(reasons, list) else [],
            }
        )
    return result


def check_pair_evidence_hypotheses(
    frontier_json: pathlib.Path,
    fixtures_root: pathlib.Path,
) -> int:
    rows = pair_evidence_hypothesis_rows(frontier_json, fixtures_root)
    missing = [
        str(row["fixture"])
        for row in rows
        if row.get("has_actionable_hypothesis") is not True
    ]
    if missing:
        print(
            "pair evidence hypotheses missing for fixture(s): "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 1
    return 0


def check_pair_evidence_hypothesis_triggers(
    frontier_json: pathlib.Path,
    fixtures_root: pathlib.Path,
    *,
    required: bool,
) -> int:
    rows = pair_evidence_hypothesis_trigger_rows(frontier_json, fixtures_root)
    gaps = pair_evidence_hypothesis_trigger_gap_details(rows)
    if required and gaps:
        print(
            "pair evidence hypothesis triggers missing for fixture(s): "
            + ", ".join(str(row["fixture"]) for row in gaps),
            file=sys.stderr,
        )
        return 1
    return 0


def print_pair_evidence_hypotheses_summary(
    frontier_json: pathlib.Path,
    fixtures_root: pathlib.Path,
    *,
    status: int,
) -> None:
    rows = pair_evidence_hypothesis_rows(frontier_json, fixtures_root)
    documented = [
        row for row in rows if row.get("has_actionable_hypothesis") is True
    ]
    print(
        "pair_evidence_hypotheses={status} documented={documented} total={total}".format(
            status="PASS" if status == 0 else "FAIL",
            documented=len(documented),
            total=len(rows),
        ),
        flush=True,
    )


def print_pair_evidence_hypothesis_triggers_summary(
    frontier_json: pathlib.Path,
    fixtures_root: pathlib.Path,
    *,
    required: bool,
) -> None:
    rows = pair_evidence_hypothesis_trigger_rows(frontier_json, fixtures_root)
    documented = [
        row for row in rows if row.get("has_actionable_hypothesis") is True
    ]
    matched = [
        row
        for row in documented
        if row.get("has_hypothesis_trigger") is True
    ]
    status = "PASS" if len(matched) == len(documented) else ("FAIL" if required else "WARN")
    print(
        "pair_evidence_hypothesis_triggers={status} matched={matched} "
        "documented={documented} total={total}".format(
            status=status,
            matched=len(matched),
            documented=len(documented),
            total=len(rows),
        ),
        flush=True,
    )
    gap_details = pair_evidence_hypothesis_trigger_gap_details(rows)
    if gap_details:
        details = [
            f"{row['fixture']}={','.join(row['pair_trigger_reasons'])}"
            for row in gap_details
        ]
        print(
            "pair_evidence_hypothesis_trigger_gaps=" + ";".join(details),
            flush=True,
        )


def check_frontier_report(frontier_json: pathlib.Path) -> int:
    summary = load_summary(frontier_json, ["verdict", "unmeasured_count"])
    verdict = summary.get("verdict")
    unmeasured_count = summary.get("unmeasured_count")
    if verdict != "PASS":
        print(f"frontier verdict {verdict!r} is not PASS", file=sys.stderr)
        return 1
    if not is_strict_int(unmeasured_count):
        print("frontier unmeasured count missing or malformed", file=sys.stderr)
        return 1
    if unmeasured_count != 0:
        print(
            f"frontier has {unmeasured_count} unmeasured candidate fixture(s)",
            file=sys.stderr,
        )
        return 1
    return 0


def check_frontier_stdout(frontier_json: pathlib.Path, frontier_stdout: pathlib.Path) -> int:
    try:
        stdout = frontier_stdout.read_text(encoding="utf8")
    except OSError:
        print("frontier stdout artifact missing", file=sys.stderr)
        return 1
    summary = load_summary(
        frontier_json,
        [
            "verdict",
            "fixtures_total",
            "rejected_count",
            "candidate_count",
            "pair_evidence_count",
            "unmeasured_count",
            "pair_margin_avg",
            "pair_margin_min",
            "pair_solo_wall_ratio_avg",
            "pair_solo_wall_ratio_max",
        ],
    )
    required_keys = {
        "verdict",
        "fixtures_total",
        "rejected_count",
        "candidate_count",
        "pair_evidence_count",
        "unmeasured_count",
    }
    if not required_keys.issubset(set(summary)):
        print("frontier stdout check missing summary fields", file=sys.stderr)
        return 1
    count_keys = {
        "fixtures_total",
        "rejected_count",
        "candidate_count",
        "pair_evidence_count",
        "unmeasured_count",
    }
    if any(not is_strict_int(summary.get(key)) for key in count_keys):
        print("frontier stdout summary counts malformed", file=sys.stderr)
        return 1
    required_summary = (
        "fixtures={fixtures_total} rejected={rejected_count} candidates={candidate_count} "
        "pair_evidence={pair_evidence_count} unmeasured={unmeasured_count} verdict={verdict}"
    ).format(**summary)
    summary_count = stdout.splitlines().count(required_summary)
    if summary_count != 1:
        print("frontier stdout summary score row count is not exactly 1", file=sys.stderr)
        return 1
    pair_evidence_count = summary.get("pair_evidence_count")
    if pair_evidence_count > 0:
        aggregate_keys = {
            "pair_margin_avg",
            "pair_margin_min",
            "pair_solo_wall_ratio_avg",
            "pair_solo_wall_ratio_max",
        }
        if not aggregate_keys.issubset(set(summary)):
            print("frontier stdout check missing aggregate fields", file=sys.stderr)
            return 1
        if (
            not is_strict_number(summary.get("pair_margin_avg"))
            or not is_strict_int(summary.get("pair_margin_min"))
            or not is_strict_number(summary.get("pair_solo_wall_ratio_avg"))
            or not is_strict_number(summary.get("pair_solo_wall_ratio_max"))
        ):
            print("frontier stdout aggregate fields malformed", file=sys.stderr)
            return 1
        required_aggregate = (
            "pair_margin_avg={avg} pair_margin_min={min_margin} "
            "wall_avg={wall_avg} wall_max={wall_max}"
        ).format(
            avg=format_decimal_margin(summary.get("pair_margin_avg")),
            min_margin=format_margin(summary.get("pair_margin_min")),
            wall_avg=format_wall_ratio(summary.get("pair_solo_wall_ratio_avg")),
            wall_max=format_wall_ratio(summary.get("pair_solo_wall_ratio_max")),
        )
        aggregate_count = stdout.splitlines().count(required_aggregate)
        if aggregate_count != 1:
            print("frontier stdout aggregate score row count is not exactly 1", file=sys.stderr)
            return 1
    expected_rows = load_pair_evidence_rows(frontier_json)
    stdout_score_rows = [
        line
        for line in stdout.splitlines()
        if "verdict=pair_evidence_passed" in line
    ]
    if len(stdout_score_rows) != len(expected_rows):
        print(
            f"frontier stdout score row count {len(stdout_score_rows)} "
            f"does not match frontier evidence row count {len(expected_rows)}",
            file=sys.stderr,
        )
        return 1
    for row in expected_rows:
        required_row = (
            "{fixture}: bare={bare_score} solo_claude={solo_score} pair={pair_score} "
            "arm={pair_arm} margin={pair_margin:+d} wall={wall} run={run_id} "
            "verdict=pair_evidence_passed triggers={triggers} "
            "hypothesis_trigger={hypothesis_trigger}"
        ).format(
            **row,
            wall=format_wall_ratio(row.get("pair_solo_wall_ratio")),
            triggers=format_trigger_reasons(row.get("pair_trigger_reasons")),
            hypothesis_trigger=format_bool(row.get("pair_trigger_has_hypothesis_reason")),
        )
        if required_row not in stdout:
            print(f"frontier stdout missing score row for {row['fixture']}", file=sys.stderr)
            return 1
    if summary["verdict"] not in {"PASS", "FAIL"}:
        print("frontier stdout verdict malformed", file=sys.stderr)
        return 1
    final_verdict_count = stdout.splitlines().count(
        f"{summary['verdict']} pair-candidate-frontier"
    )
    if final_verdict_count != 1:
        print("frontier stdout final verdict row count is not exactly 1", file=sys.stderr)
        return 1
    return 0


def format_wall_ratio(value: object) -> str:
    return f"{value:.2f}x" if is_strict_number(value) else ""


def format_decimal_margin(value: object) -> str:
    return f"{value:+.2f}" if is_strict_number(value) else ""


def format_margin(value: object) -> str:
    return f"{value:+d}" if is_strict_int(value) else ""


def format_count(value: object) -> str:
    return str(value) if is_strict_int(value) else "MISSING"


def format_trigger_reasons(value: object) -> str:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return ""
    return ",".join(value)


def format_bool(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else ""


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
        default=SCRIPT_DIR / "pair-rejected-fixtures.sh",
    )
    parser.add_argument(
        "--results-root",
        type=pathlib.Path,
        default=pathlib.Path("benchmark/auto-resolve/results"),
    )
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        help="optional directory for audit.json, frontier.json, and headroom-audit.json",
    )
    parser.add_argument(
        "--min-pair-evidence",
        type=int,
        default=4,
        help="minimum active fixtures with passing pair evidence required for PASS",
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
    parser.add_argument(
        "--require-hypothesis-trigger",
        action="store_true",
        help=(
            "fail if pair-evidence fixtures with actionable solo-headroom hypotheses "
            "do not expose spec.solo_headroom_hypothesis in trigger reasons"
        ),
    )
    args = parser.parse_args()
    if args.min_pair_evidence < 1:
        print("error: --min-pair-evidence must be >= 1", file=sys.stderr)
        return 2
    if args.min_pair_margin < 1:
        print("error: --min-pair-margin must be >= 1", file=sys.stderr)
        return 2
    if not math.isfinite(args.max_pair_solo_wall_ratio) or args.max_pair_solo_wall_ratio <= 0:
        print("error: --max-pair-solo-wall-ratio must be finite and > 0", file=sys.stderr)
        return 2

    out_dir = args.out_dir
    temp_dir = None
    if out_dir is None:
        temp_dir = tempfile.TemporaryDirectory()
        report_dir = pathlib.Path(temp_dir.name)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        report_dir = out_dir

    common = [
        "--fixtures-root",
        str(args.fixtures_root),
        "--registry",
        str(args.registry),
        "--results-root",
        str(args.results_root),
    ]
    frontier_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "pair-candidate-frontier.py"),
        *common,
        "--fail-on-unmeasured",
        "--min-pair-margin",
        str(args.min_pair_margin),
        "--max-pair-solo-wall-ratio",
        str(args.max_pair_solo_wall_ratio),
        "--out-json",
        str(report_dir / "frontier.json"),
    ]
    headroom_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "audit-headroom-rejections.py"),
        *common,
        "--min-pair-margin",
        str(args.min_pair_margin),
        "--max-pair-solo-wall-ratio",
        str(args.max_pair_solo_wall_ratio),
        "--out-json",
        str(report_dir / "headroom-audit.json"),
    ]

    frontier_stdout_path = report_dir / "frontier.stdout"
    frontier_stderr_path = report_dir / "frontier.stderr"
    headroom_stdout_path = report_dir / "headroom-rejections.stdout"
    headroom_stderr_path = report_dir / "headroom-rejections.stderr"
    frontier_status = run_check(
        "frontier",
        frontier_cmd,
        stdout_path=frontier_stdout_path,
        stderr_path=frontier_stderr_path,
    )
    headroom_status = run_check(
        "headroom-rejections",
        headroom_cmd,
        stdout_path=headroom_stdout_path,
        stderr_path=headroom_stderr_path,
    )
    frontier_report_status = check_frontier_report(report_dir / "frontier.json")
    frontier_stdout_status = check_frontier_stdout(
        report_dir / "frontier.json",
        frontier_stdout_path,
    )
    headroom_report_status = check_headroom_audit_report(
        report_dir / "headroom-audit.json",
    )
    print_headroom_rejections_summary(
        report_dir / "headroom-audit.json",
        status=headroom_report_status,
    )
    pair_evidence_status = check_min_pair_evidence(
        report_dir / "frontier.json",
        args.min_pair_evidence,
    )
    pair_evidence_quality_status = check_pair_evidence_quality(
        report_dir / "frontier.json",
        min_pair_margin=args.min_pair_margin,
        max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
    )
    print_pair_evidence_quality(
        report_dir / "frontier.json",
        min_pair_margin=args.min_pair_margin,
        max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
        status=pair_evidence_quality_status,
    )
    pair_trigger_reason_status = check_pair_trigger_reasons(
        report_dir / "frontier.json",
    )
    print_pair_trigger_reasons_summary(
        report_dir / "frontier.json",
        status=pair_trigger_reason_status,
    )
    pair_evidence_hypothesis_status = check_pair_evidence_hypotheses(
        report_dir / "frontier.json",
        args.fixtures_root,
    )
    print_pair_evidence_hypotheses_summary(
        report_dir / "frontier.json",
        args.fixtures_root,
        status=pair_evidence_hypothesis_status,
    )
    pair_evidence_hypothesis_trigger_status = check_pair_evidence_hypothesis_triggers(
        report_dir / "frontier.json",
        args.fixtures_root,
        required=args.require_hypothesis_trigger,
    )
    print_pair_evidence_hypothesis_triggers_summary(
        report_dir / "frontier.json",
        args.fixtures_root,
        required=args.require_hypothesis_trigger,
    )
    if out_dir:
        write_audit_report(
            out_dir=out_dir,
            frontier_status=frontier_status,
            headroom_status=headroom_status,
            min_pair_evidence=args.min_pair_evidence,
            min_pair_margin=args.min_pair_margin,
            max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
            frontier_report_status=frontier_report_status,
            frontier_stdout_status=frontier_stdout_status,
            headroom_report_status=headroom_report_status,
            pair_evidence_status=pair_evidence_status,
            pair_evidence_quality_status=pair_evidence_quality_status,
            pair_trigger_reason_status=pair_trigger_reason_status,
            pair_evidence_hypothesis_status=pair_evidence_hypothesis_status,
            pair_evidence_hypothesis_trigger_status=pair_evidence_hypothesis_trigger_status,
            require_hypothesis_trigger=args.require_hypothesis_trigger,
            fixtures_root=args.fixtures_root,
        )
    if temp_dir is not None:
        temp_dir.cleanup()
    if (
        frontier_status != 0
        or headroom_status != 0
        or frontier_report_status != 0
        or frontier_stdout_status != 0
        or headroom_report_status != 0
        or pair_evidence_status != 0
        or pair_evidence_quality_status != 0
        or pair_trigger_reason_status != 0
        or pair_evidence_hypothesis_status != 0
        or pair_evidence_hypothesis_trigger_status != 0
    ):
        print("FAIL audit-pair-evidence", file=sys.stderr, flush=True)
        return 1
    print("PASS audit-pair-evidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
