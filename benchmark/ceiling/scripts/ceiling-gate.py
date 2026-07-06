#!/usr/bin/env python3
"""Selection and verdict gate for the iter-0064 ceiling pilot."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CEILING_ROOT = HERE.parent
REPO_ROOT = CEILING_ROOT.parent.parent
RESULTS_ROOT = CEILING_ROOT / "results"
CORPUS_ROOT = CEILING_ROOT / "corpus"
JUDGE_QUALITY_ROOT = REPO_ROOT / "benchmark/probes/judge-quality"
CLAIM_SHAPE = "current devlyn stack (sonnet orchestrator + codex executor) vs codex bare/copycat, matched wall"
AXES = [
    "design_coherence",
    "robustness",
    "spec_long_horizon_consistency",
    "maintainability_api_ergonomics",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def task_ids(selected: str | None) -> list[str]:
    if selected:
        return [part for part in selected.split(",") if part]
    manifest = read_json(CORPUS_ROOT / "manifest.json")
    return list(manifest["tasks"].keys())


def attempt_dir(run_id: str, task: str, arm_attempt: str) -> Path:
    return RESULTS_ROOT / run_id / task / arm_attempt


def load_timing(run_id: str, task: str, arm_attempt: str) -> dict[str, Any] | None:
    path = attempt_dir(run_id, task, arm_attempt) / "timing.json"
    return read_json(path) if path.exists() else None


def load_objective(run_id: str, task: str, arm_attempt: str) -> dict[str, Any] | None:
    path = attempt_dir(run_id, task, arm_attempt) / "objective.json"
    return read_json(path) if path.exists() else None


def is_successful_bounded(timing: dict[str, Any] | None) -> bool:
    return bool(timing and int(timing.get("invoke_exit", 1)) == 0 and not timing.get("timed_out", False))


def half_up_round(value: float) -> int:
    return int(math.floor(value + 0.5))


def n_rule(run_id: str, task: str) -> dict[str, Any]:
    a1 = load_timing(run_id, task, "A1")
    b1 = load_timing(run_id, task, "B1")
    if not a1:
        return {"task": task, "status": "INVALID-missing-A1", "n": None}
    if is_successful_bounded(b1):
        denominator_attempt = "B1"
        denominator = b1
        retry_used = False
    else:
        b2 = load_timing(run_id, task, "B2")
        if is_successful_bounded(b2):
            denominator_attempt = "B2"
            denominator = b2
            retry_used = True
        else:
            return {
                "task": task,
                "status": "INVALID-infra",
                "n": None,
                "retry_used": bool(b1),
                "b1_exit": None if not b1 else b1.get("invoke_exit"),
                "b2_exit": None if not b2 else b2.get("invoke_exit"),
            }
    a_elapsed = max(float(a1.get("elapsed_seconds", 0)), 1.0)
    b_elapsed = max(float(denominator.get("elapsed_seconds", 0)), 1.0)
    ratio = a_elapsed / b_elapsed
    n = max(1, min(3, half_up_round(ratio)))
    return {
        "task": task,
        "status": "VALID",
        "n": n,
        "wall_A_seconds": a_elapsed,
        "wall_B_first_seconds": b_elapsed,
        "wall_ratio": ratio,
        "denominator_attempt": denominator_attempt,
        "retry_used": retry_used,
    }


def attempts_for_arm(run_id: str, task: str, arm: str) -> list[str]:
    root = RESULTS_ROOT / run_id / task
    if not root.exists():
        return []
    attempts = [path.name for path in root.iterdir() if path.is_dir() and re.match(rf"^{arm}[0-9]+$", path.name)]
    return sorted(attempts, key=lambda value: int(value[1:]))


def objective_score(obj: dict[str, Any] | None) -> float:
    if not obj:
        return -1.0
    if obj.get("resolved"):
        return 1.0
    if obj.get("f2p_total"):
        return float(obj.get("f2p_passed", 0)) / max(float(obj["f2p_total"]), 1.0)
    if obj.get("tests_total"):
        return float(obj.get("tests_passed", 0)) / max(float(obj["tests_total"]), 1.0)
    return 0.0


def regression_count(obj: dict[str, Any] | None) -> int:
    if not obj:
        return 10**9
    if "p2p_regressions" in obj:
        return int(obj.get("p2p_regressions") or 0)
    if "hidden_test_failures" in obj:
        return int(obj.get("hidden_test_failures") or 0)
    if obj.get("tests_total") is not None:
        return max(int(obj.get("tests_total") or 0) - int(obj.get("tests_passed") or 0), 0)
    return 10**9


def choose_best(run_id: str, task: str, arm: str) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for attempt in attempts_for_arm(run_id, task, arm):
        obj = load_objective(run_id, task, attempt)
        if obj is None:
            continue
        candidates.append({
            "arm_attempt": attempt,
            "objective_score": objective_score(obj),
            "regression_count": regression_count(obj),
            "attempt_number": int(attempt[1:]),
            "resolved": bool(obj.get("resolved")),
        })
    if not candidates:
        return None
    candidates.sort(key=lambda row: (-row["objective_score"], row["regression_count"], row["attempt_number"]))
    chosen = dict(candidates[0])
    chosen["panel_rank_tiebreak"] = "not_applied_before_blind_judge"
    chosen["candidates"] = [dict(candidate) for candidate in candidates]
    return chosen


def selection(run_id: str, tasks: list[str]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    select_args: list[str] = []
    for task in tasks:
        n = n_rule(run_id, task)
        row: dict[str, Any] = {"task": task, "n_rule": n}
        if n["status"] != "VALID":
            row["row_status"] = n["status"]
            rows[task] = row
            continue
        best_b = choose_best(run_id, task, "B")
        best_c = choose_best(run_id, task, "C")
        if best_b is None or best_c is None or load_objective(run_id, task, "A1") is None:
            row["row_status"] = "INVALID-missing-objective"
            row["best_B"] = best_b
            row["best_C"] = best_c
            rows[task] = row
            continue
        row.update({"row_status": "VALID", "best_B": best_b, "best_C": best_c, "A": "A1"})
        rows[task] = row
        select_args.extend(["--select", f"{task}={best_b['arm_attempt']}", "--select", f"{task}={best_c['arm_attempt']}"])
    return {"run_id": run_id, "tasks": rows, "select_args": select_args}


def load_cases(cases_dir: Path) -> dict[str, dict[str, Any]]:
    cases = {}
    for path in sorted(cases_dir.glob("*.json")):
        data = read_json(path)
        cases[data["id"]] = data
    return cases


def judge_certification() -> dict[str, Any]:
    cases_dir = Path(os.environ.get("CEILING_JUDGE_QUALITY_CASES", str(JUDGE_QUALITY_ROOT / "cases")))
    results_dir = Path(os.environ.get("CEILING_JUDGE_QUALITY_RESULTS", str(JUDGE_QUALITY_ROOT / "results")))
    cases = load_cases(cases_dir)
    expected_axis_totals = {"no_workaround": 0, "scope_discipline": 0}
    expected_clean = 0
    for case in cases.values():
        gt = case.get("ground_truth", {})
        if gt.get("type") == "clean":
            expected_clean += 2
        else:
            expected_axis_totals[gt.get("class")] += 2
    out: dict[str, Any] = {}
    for judge in ("sonnet", "codex"):
        judge_dir = results_dir / judge
        identity_path = judge_dir / "identity.json"
        identity = read_json(identity_path) if identity_path.exists() else {}
        axis_hits = {"no_workaround": 0, "scope_discipline": 0}
        axis_totals = {"no_workaround": 0, "scope_discipline": 0}
        clean_total = 0
        false_positives = 0
        missing: list[str] = []
        for case_id, case in cases.items():
            gt = case.get("ground_truth", {})
            for rep in (1, 2):
                path = judge_dir / f"{case_id}-rep{rep}.json"
                if not path.exists():
                    missing.append(f"{case_id}-rep{rep}")
                    continue
                record = read_json(path)
                if gt.get("type") == "clean":
                    clean_total += 1
                    if record.get("false_positive") is True:
                        false_positives += 1
                else:
                    axis = gt.get("class")
                    axis_totals[axis] += 1
                    if record.get("hit") is True:
                        axis_hits[axis] += 1
        axis_recall = {
            axis: (axis_hits[axis] / axis_totals[axis]) if axis_totals[axis] else 0.0
            for axis in axis_hits
        }
        fp_rate = (false_positives / clean_total) if clean_total else 1.0
        complete = (
            all(axis_totals[axis] >= expected_axis_totals[axis] for axis in expected_axis_totals)
            and clean_total >= expected_clean
            and not missing
        )
        certified = (
            bool(identity.get("cli_version"))
            and complete
            and all(value >= 0.75 for value in axis_recall.values())
            and fp_rate <= 0.125
        )
        out[judge] = {
            "certified": certified,
            "identity": identity,
            "axis_recall": axis_recall,
            "false_positive_rate": fp_rate,
            "axis_totals": axis_totals,
            "clean_total": clean_total,
            "missing": missing,
            "thresholds": {"axis_recall_min": 0.75, "false_positive_rate_max": 0.125},
        }
    return out


def resolved(run_id: str, task: str, arm_attempt: str | None) -> bool:
    if not arm_attempt:
        return False
    obj = load_objective(run_id, task, arm_attempt)
    return bool(obj and obj.get("resolved"))


def oracle_smoke_ok() -> bool:
    path = RESULTS_ROOT / "oracle-smoke" / "gold.iter0064-oracle-smoke.json"
    if not path.exists():
        return False
    data = read_json(path)
    return int(data.get("resolved_instances", 0)) >= 2 and not data.get("error_instances")


def ranked_axes_counts(run_id: str, valid_rows: dict[str, Any], certified_judges: list[str]) -> dict[str, Any]:
    aggregate_path = RESULTS_ROOT / run_id / "ceiling-judge-aggregate.json"
    counts = {"A_win": 0, "C_win": 0, "tie": 0, "total": 0}
    by_task: dict[str, Any] = {}
    if not aggregate_path.exists():
        return {"counts": counts, "by_task": by_task, "aggregate_path": None}
    aggregate = read_json(aggregate_path)
    for task in valid_rows:
        task_agg = (aggregate.get("tasks") or {}).get(task) or {}
        by_task[task] = {}
        for axis in AXES:
            axis_agg = ((task_agg.get("axes") or {}).get(axis) or {})
            by_task[task][axis] = {}
            for judge in certified_judges:
                outcome = (((axis_agg.get("per_judge") or {}).get(judge) or {}).get("a_vs_c"))
                if outcome in {"A_win", "C_win", "tie"}:
                    counts[outcome] += 1
                    counts["total"] += 1
                    by_task[task][axis][judge] = outcome
    return {"counts": counts, "by_task": by_task, "aggregate_path": str(aggregate_path)}


def verdict(run_id: str, tasks: list[str]) -> dict[str, Any]:
    sel = selection(run_id, tasks)
    cert = judge_certification()
    certified_judges = [judge for judge, row in cert.items() if row["certified"]]
    valid_rows = {task: row for task, row in sel["tasks"].items() if row.get("row_status") == "VALID"}
    invalid_rows = {task: row for task, row in sel["tasks"].items() if row.get("row_status") != "VALID"}
    blocking_invalid = {task: row for task, row in invalid_rows.items() if row.get("row_status") != "INVALID-infra"}
    lc4_reasons: list[str] = []
    if not oracle_smoke_ok():
        lc4_reasons.append("oracle-smoke-failed-or-missing")
    if not certified_judges:
        lc4_reasons.append("zero-certified-judges")
    if blocking_invalid:
        lc4_reasons.append("missing-required-artifacts")
    if not valid_rows:
        lc4_reasons.append("zero-valid-task-rows")

    a_sum = sum(1 for task in valid_rows if resolved(run_id, task, "A1"))
    b_sum = sum(1 for task, row in valid_rows.items() if resolved(run_id, task, row["best_B"]["arm_attempt"]))
    c_sum = sum(1 for task, row in valid_rows.items() if resolved(run_id, task, row["best_C"]["arm_attempt"]))
    ratios = [row["n_rule"]["wall_ratio"] for row in valid_rows.values() if row["n_rule"].get("wall_ratio") is not None]
    mean_wall_ratio = sum(ratios) / len(ratios) if ratios else None
    objective_moat = a_sum > c_sum

    ranked = ranked_axes_counts(run_id, valid_rows, certified_judges)
    ranked_counts = ranked["counts"]
    if len(certified_judges) >= 2 and ranked_counts["total"] > 0:
        ranked_axes_mode = "certified-panel"
        ranked_majority = ranked_counts["A_win"] > (ranked_counts["total"] / 2)
    else:
        ranked_axes_mode = "low-confidence-annex"
        ranked_majority = False
    moat_shown = objective_moat or ranked_majority

    if lc4_reasons:
        final = "INVALID"
    elif mean_wall_ratio is not None and mean_wall_ratio > 3.0:
        final = "FAIL-pilot"
    elif a_sum < b_sum:
        final = "FAIL-pilot"
    elif a_sum == b_sum:
        final = "BARE-LIFT-NOT-SHOWN"
    elif not moat_shown:
        final = "MOAT-NOT-SHOWN"
    else:
        final = "PASS-pilot"

    return {
        "run_id": run_id,
        "claim_shape": CLAIM_SHAPE,
        "verdict": final,
        "selection": sel,
        "judge_certification": cert,
        "certified_judges": certified_judges,
        "invalid_rows_excluded": invalid_rows,
        "loss_conditions": {
            "LC1_stack_vs_bare": {"A_resolved": a_sum, "best_B_resolved": b_sum},
            "LC2_moat": {
                "A_resolved": a_sum,
                "best_C_resolved": c_sum,
                "objective_moat": objective_moat,
                "ranked_axes_mode": ranked_axes_mode,
                "ranked_counts": ranked_counts,
                "ranked_majority": ranked_majority,
                "moat_shown": moat_shown,
                "ranked_axes_annex": ranked,
            },
            "LC3_efficiency": {"mean_wall_ratio": mean_wall_ratio, "cap": 3.0},
            "LC4_instrument_invalid": {"reasons": lc4_reasons},
        },
    }


def leave_one_out_note(data: dict[str, Any], excluded: str) -> str:
    rows = {
        task: row for task, row in data["selection"]["tasks"].items()
        if task != excluded and row.get("row_status") == "VALID"
    }
    if not rows:
        return f"Excluding {excluded}: no valid rows remain."
    run_id = data["run_id"]
    a_sum = sum(1 for task in rows if resolved(run_id, task, "A1"))
    b_sum = sum(1 for task, row in rows.items() if resolved(run_id, task, row["best_B"]["arm_attempt"]))
    c_sum = sum(1 for task, row in rows.items() if resolved(run_id, task, row["best_C"]["arm_attempt"]))
    lc1 = "A>B" if a_sum > b_sum else "A==B" if a_sum == b_sum else "A<B"
    moat = "A>C" if a_sum > c_sum else "A<=C"
    return f"Excluding {excluded}: objective sums are A={a_sum}, best-B={b_sum}, best-C={c_sum}; LC1 relation {lc1}, objective moat relation {moat}."


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Ceiling Verdict",
        "",
        f"Claim shape: {CLAIM_SHAPE}",
        "",
        f"Verdict: **{data['verdict']}**",
        "",
        "## Per-Task Rows",
        "",
        "| task | status | selected B | selected C | A resolved | B resolved | C resolved | N | wall ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    run_id = data["run_id"]
    for task, row in data["selection"]["tasks"].items():
        if row.get("row_status") == "VALID":
            b = row["best_B"]["arm_attempt"]
            c = row["best_C"]["arm_attempt"]
            n = row["n_rule"]["n"]
            ratio = f"{row['n_rule']['wall_ratio']:.3f}"
            lines.append(
                f"| {task} | VALID | {b} | {c} | {resolved(run_id, task, 'A1')} | "
                f"{resolved(run_id, task, b)} | {resolved(run_id, task, c)} | {n} | {ratio} |"
            )
        else:
            lines.append(f"| {task} | {row.get('row_status')} |  |  |  |  |  |  |  |")
    lines.extend([
        "",
        "## Loss Conditions",
        "",
        f"- LC1 stack vs bare: A={data['loss_conditions']['LC1_stack_vs_bare']['A_resolved']} vs best-B={data['loss_conditions']['LC1_stack_vs_bare']['best_B_resolved']}.",
        f"- LC2 moat: objective_moat={data['loss_conditions']['LC2_moat']['objective_moat']}; ranked_axes_mode={data['loss_conditions']['LC2_moat']['ranked_axes_mode']}; ranked_counts={data['loss_conditions']['LC2_moat']['ranked_counts']}.",
        f"- LC3 mean wall ratio: {data['loss_conditions']['LC3_efficiency']['mean_wall_ratio']}.",
        f"- LC4 invalid reasons: {', '.join(data['loss_conditions']['LC4_instrument_invalid']['reasons']) or 'none'}.",
        "",
        "## Leave-One-Out",
        "",
    ])
    for task in data["selection"]["tasks"]:
        lines.append(f"- {leave_one_out_note(data, task)}")
    if "FS1-schedule-max-runs" not in data["selection"]["tasks"]:
        lines.append("- FS1-schedule-max-runs was not part of this run subset; FS1 leave-one-out sensitivity is not computable.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", choices=["select", "verdict"], default="verdict")
    parser.add_argument("--select-only", action="store_true", help="Alias for --phase select")
    parser.add_argument("--tasks", help="Optional comma-separated task subset")
    args = parser.parse_args()
    if args.select_only:
        args.phase = "select"
    tasks = task_ids(args.tasks)
    run_root = RESULTS_ROOT / args.run_id
    run_root.mkdir(parents=True, exist_ok=True)

    if args.phase == "select":
        data = selection(args.run_id, tasks)
        write_json(run_root / "ceiling-selection.json", data)
        (run_root / "ceiling-select-args.txt").write_text("\n".join(data["select_args"]) + ("\n" if data["select_args"] else ""), encoding="utf-8")
        print("\n".join(data["select_args"]))
        return 0

    data = verdict(args.run_id, tasks)
    write_json(run_root / "ceiling-verdict.json", data)
    write_markdown(run_root / "ceiling-verdict.md", data)
    print(json.dumps({"verdict": data["verdict"], "path": str(run_root / "ceiling-verdict.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
