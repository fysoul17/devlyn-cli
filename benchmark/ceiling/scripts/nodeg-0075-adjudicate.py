#!/usr/bin/env python3
"""Adjudicate the frozen iter-0075 P-A/P-B/P-C and FS-0075-D rules."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path


class AdjudicationError(ValueError):
    pass


def load_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdjudicationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AdjudicationError(f"JSON object required: {path}")
    return value


def numeric(row: dict, field: str) -> int | float:
    value = row.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise AdjudicationError(f"attribution.{field} must be finite numeric")
    return value


def threshold_leg(rows: list[dict], denominator_field: str) -> dict:
    threshold = math.ceil(len(rows) / 2)
    hits = []
    per_row = []
    for row in rows:
        attribution = row["attribution"]
        denominator = numeric(attribution, denominator_field)
        allocated = sum(
            numeric(attribution, field)
            for field in (
                "interphase_gap_ms",
                "outer_loop_gap_ms",
                "censored_open_span_ms",
            )
        )
        if denominator_field == "non_phase_residual_ms":
            allocated += numeric(attribution, "startup_ms") + numeric(attribution, "tail_ms")
        unallocated = denominator - allocated
        ratio = unallocated / denominator if denominator > 0 else 0.0
        fired = ratio >= 0.20
        if fired:
            hits.append(row["control_id"])
        per_row.append(
            {
                "control_id": row["control_id"],
                "unallocated_ms": unallocated,
                "denominator_ms": denominator,
                "unallocated_ratio": ratio,
                "fired": fired,
            }
        )
    return {
        "population": len(rows),
        "half": threshold,
        "fired_count": len(hits),
        "fired_rows": hits,
        "per_row": per_row,
        "verdict": "BLOCK" if rows and len(hits) >= threshold else "PASS",
    }


def adjudicate(verdict: dict, rows: list[dict]) -> dict:
    complete_verify = [row for row in rows if row["attribution"].get("verify_complete") is True]
    pa_hits = [
        row["control_id"]
        for row in complete_verify
        if implement_share(row) >= 0.60
    ]
    if len(complete_verify) < 5:
        pa_verdict = "INCONCLUSIVE"
    elif len(pa_hits) >= 5:
        pa_verdict = "CONFIRMS"
    else:
        pa_verdict = "REFUTES"

    decomposition_complete = [
        row for row in rows if row["attribution"].get("decomposition_status") == "complete"
    ]
    pb_half = math.ceil(len(decomposition_complete) / 2)
    pb_hits = []
    pb_rows = []
    for row in decomposition_complete:
        attribution = row["attribution"]
        residual = numeric(attribution, "non_phase_residual_ms")
        named = sum(
            numeric(attribution, field)
            for field in ("startup_ms", "interphase_gap_ms", "outer_loop_gap_ms")
        )
        ratio = named / residual if residual > 0 else 0.0
        passed = ratio >= 0.50
        if passed:
            pb_hits.append(row["control_id"])
        pb_rows.append(
            {
                "control_id": row["control_id"],
                "named_ms": named,
                "residual_ms": residual,
                "ratio": ratio,
                "passed": passed,
            }
        )
    if not decomposition_complete:
        pb_verdict = "INCONCLUSIVE"
    else:
        pb_verdict = "CONFIRMS" if len(pb_hits) >= pb_half else "REFUTES"

    bars = verdict.get("bars")
    if not isinstance(bars, dict):
        raise AdjudicationError("nodeg-verdict.bars must be an object")
    quality_rows = (bars.get("quality") or {}).get("per_row")
    wall_rows = (bars.get("wall") or {}).get("per_row")
    if not isinstance(quality_rows, dict) or not isinstance(wall_rows, dict):
        raise AdjudicationError("nodeg-verdict quality/wall per_row objects required")
    selected = [row["control_id"] for row in rows]
    quality_passes = sum(
        quality_rows.get(control, {}).get("passed") is True for control in selected
    )
    wall_ratios = []
    for control in selected:
        value = wall_rows.get(control, {}).get("a_to_frozen_b_ratio")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise AdjudicationError(f"wall ratio missing for {control}")
        wall_ratios.append(value)
    wall_median = statistics.median(wall_ratios) if wall_ratios else None
    pc_population_complete = len(rows) == 7
    pc_confirmed = (
        pc_population_complete
        and quality_passes == 0
        and wall_median is not None
        and wall_median >= 8
    )

    legacy_rows = [
        row for row in rows if row["attribution"].get("decomposition_status") == "legacy-partial"
    ]
    d1_rows = []
    for row in legacy_rows:
        copied = dict(row)
        copied["attribution"] = dict(row["attribution"])
        copied["attribution"]["legacy_interior_ms"] = normalized(
            numeric(row["attribution"], "non_phase_residual_ms")
            - numeric(row["attribution"], "legacy_edge_residual_ms")
        )
        d1_rows.append(copied)

    return {
        "schema_version": 1,
        "run_id": verdict.get("run_id"),
        "row_count": len(rows),
        "P-A": {
            "complete_verify_count": len(complete_verify),
            "complete_verify_rows": [row["control_id"] for row in complete_verify],
            "implement_share_ge_0_60_count": len(pa_hits),
            "implement_share_ge_0_60_rows": pa_hits,
            "completeness_prediction_passed": len(complete_verify) >= 5,
            "verdict": pa_verdict,
        },
        "P-B": {
            "population": len(decomposition_complete),
            "half": pb_half,
            "passed_count": len(pb_hits),
            "passed_rows": pb_hits,
            "per_row": pb_rows,
            "verdict": pb_verdict,
        },
        "P-C": {
            "population": len(rows),
            "expected_population": 7,
            "quality_pass_count": quality_passes,
            "quality_zero_of_n": quality_passes == 0 and bool(rows),
            "quality_zero_of_7": pc_population_complete and quality_passes == 0,
            "wall_median_ratio": wall_median,
            "wall_median_ge_8": wall_median is not None and wall_median >= 8,
            "verdict": (
                "INCONCLUSIVE"
                if not pc_population_complete
                else "CONFIRMS" if pc_confirmed else "REFUTES"
            ),
        },
        "FS-0075-D": {
            "D1_legacy_interior": threshold_leg(d1_rows, "legacy_interior_ms"),
            "D2_complete_rows": threshold_leg(
                decomposition_complete, "non_phase_residual_ms"
            ),
        },
    }


def normalized(value: int | float) -> int | float:
    rounded = round(value, 3)
    return int(rounded) if rounded == int(rounded) else rounded


def implement_share(row: dict) -> float:
    elapsed = numeric(row["attribution"], "elapsed_ms")
    if elapsed <= 0:
        raise AdjudicationError("attribution.elapsed_ms must be > 0")
    return numeric(row["attribution"], "implement_total_ms") / elapsed


def rows_from_run(run_dir: Path, verdict: dict) -> list[dict]:
    selected = verdict.get("selected_controls")
    objective_rows = ((verdict.get("bars") or {}).get("objective") or {}).get("per_row")
    if not isinstance(selected, list) or not all(isinstance(value, str) for value in selected):
        raise AdjudicationError("nodeg-verdict.selected_controls must be a string array")
    if not isinstance(objective_rows, dict):
        raise AdjudicationError("nodeg-verdict objective per_row object required")
    rows = []
    for control_id in selected:
        objective = objective_rows.get(control_id)
        if not isinstance(objective, dict) or not isinstance(objective.get("task"), str):
            raise AdjudicationError(f"objective task missing for {control_id}")
        path = run_dir / objective["task"] / "A1" / "attribution.json"
        rows.append(
            {
                "control_id": control_id,
                "task": objective["task"],
                "attribution_path": str(path),
                "attribution": load_object(path),
            }
        )
    return rows


def self_test() -> int:
    attribution = {
        "verify_complete": True,
        "decomposition_status": "complete",
        "elapsed_ms": 1000,
        "implement_total_ms": 100,
        "non_phase_residual_ms": 500,
        "startup_ms": 200,
        "interphase_gap_ms": 100,
        "outer_loop_gap_ms": 0,
        "censored_open_span_ms": 50,
        "tail_ms": 150,
        "legacy_edge_residual_ms": None,
    }
    rows = [
        {"control_id": f"F{i}", "task": f"task-{i}", "attribution": dict(attribution)}
        for i in range(1, 8)
    ]
    verdict = {
        "run_id": "selftest",
        "bars": {
            "quality": {"per_row": {f"F{i}": {"passed": False} for i in range(1, 8)}},
            "wall": {
                "per_row": {
                    f"F{i}": {"a_to_frozen_b_ratio": value}
                    for i, value in enumerate((8, 9, 10, 11, 12, 13, 14), 1)
                }
            },
        },
    }
    result = adjudicate(verdict, rows)
    if result["P-A"]["verdict"] != "REFUTES":
        raise AssertionError(result["P-A"])
    if result["P-B"]["verdict"] != "CONFIRMS" or result["P-B"]["half"] != 4:
        raise AssertionError(result["P-B"])
    if result["P-C"]["verdict"] != "CONFIRMS":
        raise AssertionError(result["P-C"])
    nonseven = adjudicate(verdict, rows[:-1])["P-C"]
    if (
        nonseven["verdict"] != "INCONCLUSIVE"
        or nonseven["population"] != 6
        or nonseven["expected_population"] != 7
    ):
        raise AssertionError(nonseven)
    zero_elapsed_rows = [{**row, "attribution": dict(row["attribution"])} for row in rows]
    zero_elapsed_rows[0]["attribution"]["elapsed_ms"] = 0
    try:
        adjudicate(verdict, zero_elapsed_rows)
    except AdjudicationError as exc:
        if str(exc) != "attribution.elapsed_ms must be > 0":
            raise
    else:
        raise AssertionError("zero elapsed_ms accepted")
    if result["FS-0075-D"]["D2_complete_rows"]["verdict"] != "PASS":
        raise AssertionError(result["FS-0075-D"])
    legacy_partial = dict(attribution)
    legacy_partial.update(
        {
            "decomposition_status": "legacy-partial",
            "non_phase_residual_ms": 1200,
            "legacy_edge_residual_ms": 700,
            "interphase_gap_ms": 300,
            "outer_loop_gap_ms": 50,
            "censored_open_span_ms": 50,
            "startup_ms": None,
            "tail_ms": None,
        }
    )
    d1 = adjudicate(
        verdict,
        [{"control_id": "F1", "task": "task-1", "attribution": legacy_partial}],
    )["FS-0075-D"]["D1_legacy_interior"]
    if (
        d1["verdict"] != "BLOCK"
        or d1["per_row"][0]["unallocated_ms"] != 100
        or d1["per_row"][0]["unallocated_ratio"] != 0.20
    ):
        raise AssertionError(d1)
    print("SELFTEST PASS: nodeg-0075-adjudicate")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.run_dir is not None or args.output is not None:
            parser.error("run_dir/--output are not allowed with --self-test")
        return self_test()
    if args.run_dir is None:
        parser.error("run_dir is required unless --self-test")
    output = args.output or args.run_dir / "nodeg-0075-adjudication.json"
    try:
        verdict = load_object(args.run_dir / "nodeg-verdict.json")
        payload = adjudicate(verdict, rows_from_run(args.run_dir, verdict))
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except AdjudicationError as exc:
        print(f"ADJUDICATION_ERROR: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
