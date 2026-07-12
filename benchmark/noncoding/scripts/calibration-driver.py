#!/usr/bin/env python3
"""Randomly interleaved T0/T1 driver with one fail-closed manifest per seat cohort."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
REPO_ROOT = ROOT.parent.parent
RUNNER = SCRIPT_DIR / "run-packet-attempt.py"


class CalibrationError(RuntimeError):
    """The cohort cannot produce a valid calibration verdict."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationError(f"cannot read {path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def require_clean_freeze() -> str:
    status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=all", "--", "benchmark/noncoding"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise CalibrationError("benchmark/noncoding must be committed and clean before measured calibration")
    sha = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ).stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40,64}", sha) is None:
        raise CalibrationError("runner_commit_sha unavailable")
    return sha


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    spread = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return center - spread, center + spread


def evaluate_t0(counts: dict[str, dict[str, int]], repeats: int) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for fixture, roles in counts.items():
        good = [roles["good_a"], roles["good_b"]]
        bad = [roles["bad_dependency"], roles["bad_constraint"]]
        checks[f"{fixture}:separation"] = all(value > min(bad) for value in good)
        checks[f"{fixture}:no-op-fails"] = roles["no_op"] == 0
        checks[f"{fixture}:complete"] = all(0 <= value <= repeats for value in roles.values())
    return {"status": "PASS" if all(checks.values()) else "DEAD", "checks": checks}


def evaluate_t1(counts: dict[str, dict[str, int]], repeats: int) -> dict[str, Any]:
    if repeats != 16:
        raise CalibrationError("T1 repeats must remain frozen at 16")
    checks: dict[str, bool] = {}
    intervals: dict[str, dict[str, float]] = {}
    for fixture, roles in counts.items():
        goods = {key: roles[key] for key in ("good_a", "good_b")}
        bads = {key: roles[key] for key in ("bad_dependency", "bad_constraint")}
        for role, value in goods.items():
            checks[f"{fixture}:{role}:at-least-12"] = value >= 12
        for role, value in bads.items():
            checks[f"{fixture}:{role}:at-most-4"] = value <= 4
        checks[f"{fixture}:equivalent-good-delta"] = abs(goods["good_a"] - goods["good_b"]) <= 2
        checks[f"{fixture}:no-op-fails"] = roles["no_op"] == 0
        for good_role, good_value in goods.items():
            for bad_role, bad_value in bads.items():
                key = f"{fixture}:{good_role}-{bad_role}"
                risk_difference = (good_value - bad_value) / repeats
                good_lower, _good_upper = wilson(good_value, repeats)
                _bad_lower, bad_upper = wilson(bad_value, repeats)
                lower_95 = good_lower - bad_upper
                intervals[key] = {"risk_difference": risk_difference, "lower_95_newcombe": lower_95}
                checks[f"{key}:risk-diff-at-least-0.50"] = risk_difference >= 0.50
                checks[f"{key}:positive-95pct-interval"] = lower_95 > 0
    return {
        "status": "ADMIT" if all(checks.values()) else "DEAD",
        "checks": checks,
        "risk_difference_intervals": intervals,
    }


def schedule_for(manifest: dict[str, Any], repeats: int) -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    no_op = manifest["no_op_packet"]
    for fixture, record in sorted(manifest["fixtures"].items()):
        packets = dict(record["packets"])
        packets["no_op"] = no_op
        for role, path in packets.items():
            for attempt in range(1, repeats + 1):
                schedule.append({"fixture": fixture, "role": role, "packet": path, "attempt": attempt})
    return schedule


def counts_from(attempts: list[dict[str, Any]], fixtures: list[str]) -> dict[str, dict[str, int]]:
    roles = ("good_a", "good_b", "bad_dependency", "bad_constraint", "no_op")
    counts = {fixture: {role: 0 for role in roles} for fixture in fixtures}
    for attempt in attempts:
        if attempt["outcome"] == "resolve":
            counts[attempt["fixture"]][attempt["role"]] += 1
    return counts


def run_cohort(
    *,
    source: dict[str, Any],
    seat: str,
    tier: str,
    repeats: int,
    run_id: str,
    seed: int,
    timeout_seconds: int,
    output_root: Path,
    runner_sha: str,
) -> Path:
    cohort_id = f"{run_id}-{tier}-{seat}"
    cohort_dir = output_root / cohort_id
    manifest_path = cohort_dir / "manifest.json"
    schedule = schedule_for(source, repeats)
    random.Random(seed).shuffle(schedule)
    cohort: dict[str, Any] = {
        "schema_version": "noncoding-calibration-cohort-1",
        "tier": tier,
        "run_id": cohort_id,
        "interleave_seed": seed,
        "repeats_per_packet": repeats,
        "fixture_namespace": "calibration",
        "fixture_ids": sorted(source["fixtures"]),
        "packet_roles": ["good_a", "good_b", "bad_dependency", "bad_constraint", "no_op"],
        "thresholds": source["calibration"][tier],
        "cohort_identity": {
            "runner_commit_sha": runner_sha,
            "cli_version": None,
            "requested_alias": "gpt-5.6-terra" if seat == "terra" else "sonnet",
            "runtime_resolved_model": None,
            "run_id": cohort_id,
        },
        "interleave_order": schedule,
        "attempts": [],
        "status": "RUNNING",
    }
    write_json(manifest_path, cohort)
    identities: set[tuple[str, str, str, str]] = set()
    for ordinal, item in enumerate(schedule, start=1):
        attempt_dir = cohort_dir / "attempts" / f"{ordinal:04d}"
        command = [
            sys.executable,
            str(RUNNER),
            "--fixture",
            item["fixture"],
            "--packet",
            item["packet"],
            "--seat",
            seat,
            "--attempt",
            str(item["attempt"]),
            "--run-id",
            cohort_id,
            "--result-dir",
            str(attempt_dir),
            "--timeout-seconds",
            str(timeout_seconds),
        ]
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        result_path = attempt_dir / "result.json"
        if completed.returncode not in {0, 3} or not result_path.is_file():
            cohort["status"] = "INVALID"
            cohort["invalid_reason"] = completed.stderr.strip() or f"runner exit {completed.returncode}"
            write_json(manifest_path, cohort)
            raise CalibrationError(f"{cohort_id} attempt {ordinal} invalid: {cohort['invalid_reason']}")
        result = read_json(result_path)
        if result.get("outcome") == "INVALID":
            cohort["status"] = "INVALID"
            cohort["invalid_reason"] = result.get("provenance", {}).get("invalid_reasons")
            write_json(manifest_path, cohort)
            raise CalibrationError(f"{cohort_id} attempt {ordinal} invalid")
        provenance = result["provenance"]
        identity = (
            str(provenance["cli_version"]),
            provenance["requested_alias"],
            provenance["runtime_resolved_model"],
            provenance["runner_commit_sha"],
        )
        identities.add(identity)
        if len(identities) != 1 or identity[3] != runner_sha:
            cohort["status"] = "INVALID"
            cohort["invalid_reason"] = "cohort identity drift"
            write_json(manifest_path, cohort)
            raise CalibrationError(f"{cohort_id} identity drift")
        cohort["cohort_identity"].update(
            {"cli_version": identity[0], "runtime_resolved_model": identity[2]}
        )
        cohort["attempts"].append(
            {
                "ordinal": ordinal,
                "fixture": item["fixture"],
                "role": item["role"],
                "attempt": item["attempt"],
                "packet_id": result["packet_id"],
                "outcome": result["outcome"],
                "wall_seconds": result["wall_seconds"],
                "result_path": str(result_path),
            }
        )
        write_json(manifest_path, cohort)
    counts = counts_from(cohort["attempts"], sorted(source["fixtures"]))
    verdict = evaluate_t0(counts, repeats) if tier == "t0" else evaluate_t1(counts, repeats)
    cohort["resolve_counts"] = counts
    cohort["verdict"] = verdict
    cohort["status"] = verdict["status"]
    write_json(manifest_path, cohort)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", required=True, choices=("t0", "t1"))
    parser.add_argument("--seats", default="terra,sonnet")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--interleave-seed", required=True, type=int)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    seats = args.seats.split(",")
    if not seats or any(seat not in {"terra", "sonnet"} for seat in seats) or len(seats) != len(set(seats)):
        parser.error("--seats must be a unique comma-separated subset of terra,sonnet")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id) is None:
        parser.error("--run-id has invalid characters")
    try:
        source = read_json(ROOT / "manifest.json")
        runner_sha = require_clean_freeze()
        repeats = source["calibration"][args.tier]["repeats_per_packet"]
        paths = []
        for seat in seats:
            paths.append(
                run_cohort(
                    source=source,
                    seat=seat,
                    tier=args.tier,
                    repeats=repeats,
                    run_id=args.run_id,
                    seed=args.interleave_seed,
                    timeout_seconds=args.timeout_seconds,
                    output_root=args.output_root,
                    runner_sha=runner_sha,
                )
            )
    except (CalibrationError, KeyError, TypeError) as exc:
        print(f"CALIBRATION_INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"manifests": [str(path) for path in paths]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
