#!/usr/bin/env python3
"""Audit failed headroom artifacts against the rejected fixture registry.

The spending loop is:
  headroom FAIL -> reject/rework fixture before pair spend
  headroom PASS -> run pair gate and keep passing pair evidence

This audit catches the forgotten middle state: an active fixture has a failed
headroom-gate.json, no passing pair evidence, and no rejected-registry entry.
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
    has_canonical_pair_trigger_reason,
    has_known_pair_trigger_reason,
    loads_strict_json_object,
    normalize_pair_evidence_row,
)


def fixture_short(name: str) -> str:
    return name.split("-", 1)[0] if "-" in name else name


def sort_fixture_key(name: str) -> tuple[int, str]:
    short = fixture_short(name)
    match = re.fullmatch(r"F(\d+)", short)
    return (int(match.group(1)) if match else 10_000, name)


def active_fixtures(fixtures_root: pathlib.Path) -> set[str]:
    if not fixtures_root.is_dir():
        raise ValueError(f"fixtures root missing: {fixtures_root}")
    return {
        path.name
        for path in fixtures_root.iterdir()
        if path.is_dir() and re.fullmatch(r"F\d+-.+", path.name)
    }


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


def load_json_object(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        data = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data


def load_headroom_gate(path: pathlib.Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = loads_strict_json_object(path.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return None, "headroom-gate.json must be valid JSON object"
    return data, None


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


def fixtures_with_passing_pair_evidence(
    results_root: pathlib.Path,
    *,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float,
) -> set[str]:
    fixtures: set[str] = set()
    if not results_root.is_dir():
        return fixtures
    for gate_path in results_root.glob("*/full-pipeline-pair-gate.json"):
        gate = load_json_object(gate_path)
        if gate is None or gate.get("verdict") != "PASS":
            continue
        run_id = str(gate.get("run_id") or gate_path.parent.name)
        pair_arm = gate.get("pair_arm")
        for row in gate.get("rows", []):
            if not isinstance(row, dict) or row.get("status") != "PASS":
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
            evidence = normalize_pair_evidence_row(
                fixture=fixture,
                run_id=run_id,
                pair_arm=pair_arm,
                row=candidate_row,
            )
            if evidence is None:
                continue
            if (
                evidence["pair_margin"] >= min_pair_margin
                and evidence["pair_solo_wall_ratio"] <= max_pair_solo_wall_ratio
            ):
                fixtures.add(fixture)
    return fixtures


def failed_headroom_rows(
    *,
    fixtures_root: pathlib.Path,
    results_root: pathlib.Path,
) -> dict[str, list[dict[str, Any]]]:
    active = active_fixtures(fixtures_root)
    rows_by_fixture: dict[str, list[dict[str, Any]]] = {}
    if not results_root.is_dir():
        return rows_by_fixture
    for gate_path in sorted(results_root.glob("*/headroom-gate.json")):
        gate = load_json_object(gate_path)
        if gate is None or gate.get("verdict") != "FAIL":
            continue
        run_id = str(gate.get("run_id") or gate_path.parent.name)
        rows = gate.get("rows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("status") == "PASS":
                continue
            fixture = row.get("fixture")
            if not isinstance(fixture, str) or fixture not in active:
                continue
            observed = dict(row)
            observed["run_id"] = run_id
            rows_by_fixture.setdefault(fixture, []).append(observed)
    return rows_by_fixture


def expected_run_id(reason: str) -> str | None:
    match = re.search(r"\bin\s+([A-Za-z0-9_.:-]+)", reason)
    if not match:
        return None
    token = match.group(1)
    return token if any(char.isdigit() for char in token) else None


def expected_scores(reason: str) -> tuple[int | None, int | None]:
    pair = re.search(r"\bbare\s+(\d+)\s*/\s*solo_claude\s+(\d+)\b", reason)
    if pair:
        return int(pair.group(1)), int(pair.group(2))
    solo = re.search(r"\bsolo_claude\s+(?:scored|score)\s+(\d+)\b", reason)
    return None, int(solo.group(1)) if solo else None


def score_matches(row: dict[str, Any], expected_bare: int | None, expected_solo: int | None) -> bool:
    if expected_bare is not None and row.get("bare_score") != expected_bare:
        return False
    if expected_solo is not None and row.get("solo_score") != expected_solo:
        return False
    return True


def unsupported_registry_rejections(
    *,
    fixtures_root: pathlib.Path,
    registry: pathlib.Path,
    results_root: pathlib.Path,
) -> list[dict[str, Any]]:
    active = sorted(active_fixtures(fixtures_root), key=sort_fixture_key)
    rows_by_fixture = failed_headroom_rows(
        fixtures_root=fixtures_root,
        results_root=results_root,
    )
    unsupported: list[dict[str, Any]] = []
    for fixture in active:
        reason = rejected_reason(registry, fixture)
        if not reason:
            continue
        if "trivial calibration fixture" in reason or "known-limit ambiguity fixture" in reason:
            continue
        rows = rows_by_fixture.get(fixture, [])
        run_id = expected_run_id(reason)
        expected_bare, expected_solo = expected_scores(reason)
        matching_rows = rows
        if run_id is not None:
            matching_rows = [row for row in rows if row.get("run_id") == run_id]
        if not matching_rows:
            unsupported.append({
                "fixture": fixture,
                "reason": reason,
                "expected_run_id": run_id,
                "expected_bare_score": expected_bare,
                "expected_solo_score": expected_solo,
                "observed": rows,
                "problem": "no matching failed headroom artifact",
            })
            continue
        if not any(score_matches(row, expected_bare, expected_solo) for row in matching_rows):
            unsupported.append({
                "fixture": fixture,
                "reason": reason,
                "expected_run_id": run_id,
                "expected_bare_score": expected_bare,
                "expected_solo_score": expected_solo,
                "observed": matching_rows,
                "problem": "registry score does not match headroom artifact",
            })
    return unsupported


def unrecorded_headroom_failures(
    *,
    fixtures_root: pathlib.Path,
    registry: pathlib.Path,
    results_root: pathlib.Path,
    min_pair_margin: int,
    max_pair_solo_wall_ratio: float,
) -> list[dict[str, Any]]:
    active = active_fixtures(fixtures_root)
    rejected = registry_short_ids(registry)
    pair_passed = fixtures_with_passing_pair_evidence(
        results_root,
        min_pair_margin=min_pair_margin,
        max_pair_solo_wall_ratio=max_pair_solo_wall_ratio,
    )
    failures: list[dict[str, Any]] = []

    if not results_root.is_dir():
        return failures

    for gate_path in sorted(results_root.glob("*/headroom-gate.json")):
        gate, load_error = load_headroom_gate(gate_path)
        run_id = str(gate.get("run_id") or gate_path.parent.name) if gate else gate_path.parent.name
        if load_error:
            failures.append({
                "run_id": run_id,
                "fixture": "<unknown>",
                "status": "MALFORMED_JSON",
                "reason": load_error,
                "bare_score": None,
                "solo_score": None,
            })
            continue
        if gate.get("verdict") != "FAIL":
            continue
        rows = gate.get("rows")
        if not isinstance(rows, list) or not rows:
            failures.append({
                "run_id": run_id,
                "fixture": "<unknown>",
                "status": "MALFORMED_ROWS",
                "reason": "headroom-gate.json rows must be a non-empty array",
                "bare_score": None,
                "solo_score": None,
            })
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("status") == "PASS":
                continue
            fixture = row.get("fixture")
            if not isinstance(fixture, str) or fixture not in active:
                continue
            short = fixture_short(fixture)
            if short in rejected or fixture in pair_passed:
                continue
            status = row.get("status")
            if not isinstance(status, str) or not status:
                status = "MALFORMED"
            failures.append({
                "run_id": run_id,
                "fixture": fixture,
                "status": status,
                "reason": row.get("reason") or "",
                "bare_score": row.get("bare_score"),
                "solo_score": row.get("solo_score"),
            })

    return sorted(failures, key=lambda item: (sort_fixture_key(item["fixture"]), item["run_id"]))


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
        failures = unrecorded_headroom_failures(
            fixtures_root=args.fixtures_root,
            registry=args.registry,
            results_root=args.results_root,
            min_pair_margin=args.min_pair_margin,
            max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
        )
        unsupported_rejections = unsupported_registry_rejections(
            fixtures_root=args.fixtures_root,
            registry=args.registry,
            results_root=args.results_root,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = {
        "verdict": "PASS" if not failures and not unsupported_rejections else "FAIL",
        "unrecorded_failures": failures,
        "unsupported_registry_rejections": unsupported_rejections,
    }
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")

    if failures:
        print("unrecorded headroom rejection(s):", file=sys.stderr)
        for item in failures:
            print(
                "{run_id} {fixture}: status={status} bare={bare_score} "
                "solo_claude={solo_score} reason={reason}".format(**item),
                file=sys.stderr,
            )
    if unsupported_rejections:
        print("unsupported registry rejection(s):", file=sys.stderr)
        for item in unsupported_rejections:
            print(
                "{fixture}: problem={problem} expected_run={expected_run_id} "
                "expected_bare={expected_bare_score} expected_solo_claude={expected_solo_score} "
                "reason={reason}".format(**item),
                file=sys.stderr,
            )
    if failures or unsupported_rejections:
        return 1

    print("PASS audit-headroom-rejections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
