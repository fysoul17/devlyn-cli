#!/usr/bin/env python3
"""Deterministic G0 correlated-ledger power proof for iter-0112.

This module owns the shared 0110 decision path: task-level early/late
interaction, percentile bootstrap over complete block crossover replicates,
strict 3/20 bounds, and SATURATED precedence.  The frozen scorer imports these
functions directly.  It intentionally never opens a sealed task tree.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import pathlib
import random
import statistics
import sys
from collections import Counter, defaultdict


REPO = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_SCHEDULE = REPO / "docs/specs/iter0112/schedule.json"
SEED = 20260825
K = 8
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
ENGINES = (*MATRIX_ENGINES, "claude-sonnet-5")
ANCHORS = {
    "claude-sonnet-5": 39 / 80,
    "claude-opus-5": 0.294,
    "claude-opus-4-8": 0.475,
}
DELTA_H = 3 / 20
RHO_MEMBERS = (0.0, 0.25, 0.5)
HETEROGENEITY_SEED = 20260826
HETEROGENEITY_SPREAD = 0.08
BOOTSTRAP_SEED = 20260809
BOOTSTRAP_RESAMPLES = 1_000
DEFAULT_N_SIM = 2_000
NORMAL = statistics.NormalDist()

SCENARIOS = {
    "S-null": {"offsets": {}, "saturate_matrix_late": False},
    "S-conf": {"offsets": {"claude-opus-5": DELTA_H}, "saturate_matrix_late": False},
    "S-large": {"offsets": {"claude-opus-5": 2 * DELTA_H}, "saturate_matrix_late": False},
    "S-sat": {"offsets": {}, "saturate_matrix_late": True},
}


class ProofViolation(ValueError):
    """A named proof-input or registered-decision failure."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def percentile(sorted_values: list[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


@functools.lru_cache(maxsize=None)
def bootstrap_indices(replicate_count: int, resamples: int) -> tuple[tuple[int, ...], ...]:
    if replicate_count < 1 or resamples < 1:
        raise ProofViolation("bootstrap-shape-invalid")
    rng = random.Random(BOOTSTRAP_SEED)
    return tuple(
        tuple(rng.randrange(replicate_count) for _ in range(replicate_count))
        for _ in range(resamples)
    )


def bootstrap_ci(replicate_means: list[float], resamples: int) -> tuple[float, float]:
    count = len(replicate_means)
    values = [
        sum(replicate_means[index] for index in indexes) / count
        for indexes in bootstrap_indices(count, resamples)
    ]
    values.sort()
    return percentile(values, 0.025), percentile(values, 0.975)


def select_terminal(ci: tuple[float, float], saturated: bool) -> str:
    if saturated:
        return "SATURATED"
    if ci[0] > DELTA_H:
        return "CONFIRMED"
    if ci[1] < DELTA_H:
        return "MATERIAL_GAP_REFUTED"
    return "INCONCLUSIVE_AT_PILOT_N"


def complete_replicate_interaction(
    observations: dict[str, dict[str, tuple[float, float]]],
) -> float:
    """Return one complete crossover replicate's registered interaction."""
    if set(observations) != set(MATRIX_ENGINES):
        raise ProofViolation("replicate-engine-set-invalid")
    task_sets = {engine: set(values) for engine, values in observations.items()}
    if len({tuple(sorted(tasks)) for tasks in task_sets.values()}) != 1:
        raise ProofViolation("replicate-task-matching-invalid")
    task_ids = sorted(next(iter(task_sets.values())))
    if not task_ids:
        raise ProofViolation("replicate-task-count-invalid")
    d_values = []
    for task_id in task_ids:
        values = {}
        for engine in MATRIX_ENGINES:
            pair = observations[engine][task_id]
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ProofViolation("replicate-pair-invalid")
            values[engine] = pair
        d_values.append(
            (values[MATRIX_ENGINES[0]][1] - values[MATRIX_ENGINES[0]][0])
            - (values[MATRIX_ENGINES[1]][1] - values[MATRIX_ENGINES[1]][0])
        )
    return sum(d_values) / len(d_values)


def non_tied_pair_count(pairs: dict[str, tuple[float, float]]) -> int:
    return sum(early != late for early, late in pairs.values())


def decision_path(
    replicate_means: list[float], saturated: bool, resamples: int = BOOTSTRAP_RESAMPLES
) -> tuple[float, tuple[float, float], str]:
    """Apply the registered replicate bootstrap and terminal bijection."""
    if not replicate_means:
        raise ProofViolation("replicate-count-invalid")
    ci = bootstrap_ci(replicate_means, resamples)
    return sum(replicate_means) / len(replicate_means), ci, select_terminal(ci, saturated)


def deterministic_seed(*parts: object) -> int:
    digest = hashlib.sha256(canonical_bytes(list(parts))).digest()
    return SEED ^ int.from_bytes(digest[:8], "big")


def centered_profile(engine: str, task_ids: list[str]) -> dict[str, float]:
    rng = random.Random(deterministic_seed("heterogeneity", HETEROGENEITY_SEED, engine))
    raw = [rng.gauss(0.0, 1.0) for _ in task_ids]
    mean = sum(raw) / len(raw)
    centered = [value - mean for value in raw]
    rms = math.sqrt(sum(value * value for value in centered) / len(centered))
    if rms == 0:
        raise ProofViolation("heterogeneity-degenerate")
    rates = {
        task_id: ANCHORS[engine] + HETEROGENEITY_SPREAD * value / rms
        for task_id, value in zip(task_ids, centered, strict=True)
    }
    if any(not 0.0 < value < 1.0 for value in rates.values()):
        raise ProofViolation(f"heterogeneity-rate-out-of-range-{engine}")
    if not math.isclose(sum(rates.values()) / len(rates), ANCHORS[engine], abs_tol=1e-12):
        raise ProofViolation(f"heterogeneity-anchor-drift-{engine}")
    return rates


def parse_schedule(path: pathlib.Path) -> tuple[dict[str, object], dict[str, list[dict[str, object]]], list[str]]:
    try:
        schedule = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProofViolation(f"schedule-unreadable:{exc}") from exc
    if not isinstance(schedule, dict):
        raise ProofViolation("schedule-not-object")
    if schedule.get("schema") != "iter0110-session-horizon-schedule-v1":
        raise ProofViolation("schedule-schema-mismatch")
    if schedule.get("seed") != SEED or schedule.get("k") != K:
        raise ProofViolation("schedule-registration-mismatch")
    if schedule.get("engines") != list(ENGINES) or schedule.get("matrix_engines") != list(MATRIX_ENGINES):
        raise ProofViolation("schedule-engine-mismatch")
    blocks = schedule.get("blocks")
    sessions = schedule.get("sessions")
    if not isinstance(blocks, list) or not isinstance(sessions, list):
        raise ProofViolation("schedule-containers-invalid")
    if schedule.get("block_assignments_sha256") != hashlib.sha256(canonical_bytes(blocks)).hexdigest():
        raise ProofViolation("schedule-block-digest-mismatch")
    block_tasks: dict[str, list[str]] = {}
    for block in blocks:
        if not isinstance(block, dict):
            raise ProofViolation("schedule-block-invalid")
        replicate_id = block.get("replicate_id")
        task_ids = block.get("task_ids")
        if not isinstance(replicate_id, str) or not isinstance(task_ids, list) or len(task_ids) != K:
            raise ProofViolation("schedule-block-shape-invalid")
        block_tasks[replicate_id] = list(task_ids)
    if len(block_tasks) != len(blocks):
        raise ProofViolation("schedule-replicate-duplicate")
    sessions_by_replicate: dict[str, list[dict[str, object]]] = defaultdict(list)
    for session in sessions:
        if not isinstance(session, dict):
            raise ProofViolation("schedule-session-invalid")
        replicate_id = session.get("replicate_id")
        tasks = session.get("tasks")
        if (
            not isinstance(replicate_id, str)
            or replicate_id not in block_tasks
            or session.get("engine") not in ENGINES
            or not isinstance(tasks, list)
            or len(tasks) != K
        ):
            raise ProofViolation("schedule-session-shape-invalid")
        sessions_by_replicate[replicate_id].append(session)
    expected_sessions = len(blocks) * len(ENGINES) * 2
    if len(sessions) != expected_sessions:
        raise ProofViolation("schedule-session-count-invalid")
    for replicate_id, group in sessions_by_replicate.items():
        if len(group) != len(ENGINES) * 2:
            raise ProofViolation(f"schedule-replicate-session-count-{replicate_id}")
        positions: dict[tuple[str, str], list[str]] = defaultdict(list)
        for session in group:
            for item in session["tasks"]:
                if not isinstance(item, dict):
                    raise ProofViolation("schedule-task-invalid")
                task_id = item.get("task_id")
                position = item.get("position_class")
                if task_id not in block_tasks[replicate_id] or position not in {"EARLY", "LATE"}:
                    raise ProofViolation("schedule-task-position-invalid")
                positions[(session["engine"], task_id)].append(position)
        for engine in ENGINES:
            for task_id in block_tasks[replicate_id]:
                if sorted(positions[(engine, task_id)]) != ["EARLY", "LATE"]:
                    raise ProofViolation(f"schedule-crossover-invalid-{replicate_id}-{engine}")
    task_ids = sorted({task_id for values in block_tasks.values() for task_id in values})
    if len(task_ids) != 32:
        raise ProofViolation("schedule-task-universe-invalid")
    return schedule, sessions_by_replicate, task_ids


def probability_for(
    engine: str,
    task_id: str,
    position_class: str,
    scenario: dict[str, object],
    rates: dict[str, dict[str, float]],
) -> float:
    if position_class == "LATE" and scenario["saturate_matrix_late"] and engine in MATRIX_ENGINES:
        return 1.0
    probability = rates[engine][task_id]
    if position_class == "LATE":
        probability += float(scenario["offsets"].get(engine, 0.0))
    if not 0.0 <= probability <= 1.0:
        raise ProofViolation(f"scenario-probability-out-of-range-{engine}-{position_class}")
    return probability


def draw_failure_fraction(probability: float, shared: float, rho: float, rng: random.Random) -> float:
    if probability <= 0.0:
        return 0.0
    if probability >= 1.0:
        return 1.0
    latent = math.sqrt(rho) * shared + math.sqrt(1.0 - rho) * rng.gauss(0.0, 1.0)
    return 1.0 if latent <= NORMAL.inv_cdf(probability) else 0.0


def simulate_once(
    sessions_by_replicate: dict[str, list[dict[str, object]]],
    rates: dict[str, dict[str, float]],
    scenario: dict[str, object],
    rho: float,
    sweeps: int,
    rng: random.Random,
    bootstrap_resamples: int,
) -> tuple[str, tuple[float, float], float, dict[str, float], bool, dict[str, int]]:
    observations: dict[tuple[str, str, str], float] = {}
    active_replicates: list[str] = []
    for replicate_id, sessions in sessions_by_replicate.items():
        sweep_id = sessions[0].get("sweep_id")
        if not isinstance(sweep_id, int) or sweep_id > sweeps:
            continue
        active_replicates.append(replicate_id)
        for session in sessions:
            shared = rng.gauss(0.0, 1.0)
            engine = str(session["engine"])
            for item in session["tasks"]:
                task_id = str(item["task_id"])
                position_class = str(item["position_class"])
                key = (engine, replicate_id, task_id)
                if key in observations:
                    raise ProofViolation("duplicate-simulated-position")
                observations[key] = draw_failure_fraction(
                    probability_for(engine, task_id, position_class, scenario, rates), shared, rho, rng
                )
                # Position is needed separately; preserve it without widening the score type.
                observations[(engine, replicate_id, f"{task_id}:{position_class}")] = observations.pop(key)
    active_replicates.sort()
    replicate_means: list[float] = []
    early_means: dict[str, list[float]] = {engine: [] for engine in ENGINES}
    non_tied_pairs: dict[str, int] = {engine: 0 for engine in MATRIX_ENGINES}
    saturated = True
    for replicate_id in active_replicates:
        tasks = {
            key[2].rsplit(":", 1)[0]
            for key in observations
            if key[1] == replicate_id and key[2].endswith((":EARLY", ":LATE"))
        }
        pairs: dict[str, dict[str, tuple[float, float]]] = {engine: {} for engine in MATRIX_ENGINES}
        for task_id in tasks:
            for engine in ENGINES:
                early = observations[(engine, replicate_id, f"{task_id}:EARLY")]
                late = observations[(engine, replicate_id, f"{task_id}:LATE")]
                early_means[engine].append(early)
                if engine in MATRIX_ENGINES:
                    pairs[engine][task_id] = (early, late)
            saturated = saturated and all(pairs[engine][task_id][1] == 1.0 for engine in MATRIX_ENGINES)
        if len(pairs[MATRIX_ENGINES[0]]) != K:
            raise ProofViolation("replicate-task-count-invalid")
        replicate_means.append(complete_replicate_interaction(pairs))
        for engine in MATRIX_ENGINES:
            non_tied_pairs[engine] += non_tied_pair_count(pairs[engine])
    if len(replicate_means) != sweeps * 4:
        raise ProofViolation("replicate-count-invalid")
    delta, ci, terminal = decision_path(replicate_means, saturated, bootstrap_resamples)
    means = {engine: sum(values) / len(values) for engine, values in early_means.items()}
    return terminal, ci, delta, means, saturated, non_tied_pairs


def true_interaction(scenario_name: str) -> float:
    scenario = SCENARIOS[scenario_name]
    if scenario["saturate_matrix_late"]:
        return ANCHORS[MATRIX_ENGINES[1]] - ANCHORS[MATRIX_ENGINES[0]]
    return float(scenario["offsets"].get(MATRIX_ENGINES[0], 0.0)) - float(
        scenario["offsets"].get(MATRIX_ENGINES[1], 0.0)
    )


def summarize_cell(
    scenario_name: str,
    rho: float,
    sweeps: int,
    sessions_by_replicate: dict[str, list[dict[str, object]]],
    rates: dict[str, dict[str, float]],
    n_sim: int,
    bootstrap_resamples: int,
) -> dict[str, object]:
    scenario = SCENARIOS[scenario_name]
    rng = random.Random(deterministic_seed("simulation", scenario_name, rho, sweeps, n_sim, bootstrap_resamples))
    counts: Counter[str] = Counter()
    coverage_count = 0
    deltas: list[float] = []
    early_samples: dict[str, list[float]] = {engine: [] for engine in ENGINES}
    non_tied_samples: dict[str, list[int]] = {engine: [] for engine in MATRIX_ENGINES}
    truth = true_interaction(scenario_name)
    for _ in range(n_sim):
        terminal, ci, delta, early, _saturated, non_tied_pairs = simulate_once(
            sessions_by_replicate, rates, scenario, rho, sweeps, rng, bootstrap_resamples
        )
        counts[terminal] += 1
        coverage_count += int(ci[0] <= truth <= ci[1])
        deltas.append(delta)
        for engine in ENGINES:
            early_samples[engine].append(early[engine])
        for engine in MATRIX_ENGINES:
            non_tied_samples[engine].append(non_tied_pairs[engine])
    probabilities = {
        terminal: counts[terminal] / n_sim
        for terminal in ("CONFIRMED", "MATERIAL_GAP_REFUTED", "INCONCLUSIVE_AT_PILOT_N", "SATURATED")
    }
    return {
        "scenario": scenario_name,
        "rho": rho,
        "sweeps": sweeps,
        "replicates": sweeps * 4,
        "n_sim": n_sim,
        "true_interaction": truth,
        "terminal_probabilities": probabilities,
        "ci_coverage": coverage_count / n_sim,
        "observed_delta": {
            "mean": sum(deltas) / n_sim,
            "p025": percentile(sorted(deltas), 0.025),
            "p975": percentile(sorted(deltas), 0.975),
        },
        "g1_early_null_spread": {
            engine: {
                "anchor": ANCHORS[engine],
                "p025": percentile(sorted(values), 0.025),
                "p975": percentile(sorted(values), 0.975),
                "max_abs_deviation": max(
                    abs(percentile(sorted(values), 0.025) - ANCHORS[engine]),
                    abs(percentile(sorted(values), 0.975) - ANCHORS[engine]),
                ),
            }
            for engine, values in early_samples.items()
        }
        if scenario_name == "S-null"
        else None,
        "g3_non_tied_pair_support": {
            engine: {
                "pairs_per_engine": sweeps * 4 * K,
                "mean": sum(values) / len(values),
                "p025": percentile(sorted(values), 0.025),
                "p975": percentile(sorted(values), 0.975),
            }
            for engine, values in non_tied_samples.items()
        },
    }


def criteria_for_s(results: list[dict[str, object]], sweeps: int) -> dict[str, object]:
    cells_by_rho = {
        rho: {
            str(item["scenario"]): item
            for item in results
            if item["sweeps"] == sweeps and item["rho"] == rho
        }
        for rho in RHO_MEMBERS
    }
    if any(set(cells) != set(SCENARIOS) for cells in cells_by_rho.values()):
        raise ProofViolation("criteria-cells-missing")
    member_values = {
        "confirmed_reachable": {
            rho: cells["S-large"]["terminal_probabilities"]["CONFIRMED"]
            for rho, cells in cells_by_rho.items()
        },
        "refuted_reachable": {
            rho: cells["S-null"]["terminal_probabilities"]["MATERIAL_GAP_REFUTED"]
            for rho, cells in cells_by_rho.items()
        },
        "coverage": {
            rho: min(float(cells[name]["ci_coverage"]) for name in SCENARIOS)
            for rho, cells in cells_by_rho.items()
        },
        "false_confirmed_null": {
            rho: cells["S-null"]["terminal_probabilities"]["CONFIRMED"]
            for rho, cells in cells_by_rho.items()
        },
    }
    criteria = {}
    for name, values in member_values.items():
        maximum = name == "false_confirmed_null"
        worst_rho = max(values, key=values.get) if maximum else min(values, key=values.get)
        value = values[worst_rho]
        required = "<= 0.05" if maximum else (">= 0.9" if name == "coverage" else "> 0.5")
        passed = value <= 0.05 if maximum else (value >= 0.9 if name == "coverage" else value > 0.5)
        criteria[name] = {
            "members": {str(rho): values[rho] for rho in RHO_MEMBERS},
            "worst_rho": worst_rho,
            "value": value,
            "required": required,
            "passed": passed,
        }
    return {
        "sweeps": sweeps,
        "evaluated_rhos": list(RHO_MEMBERS),
        "criteria": criteria,
        "passed": all(item["passed"] for item in criteria.values()),
    }


def run_grid(
    schedule: dict[str, object],
    sessions_by_replicate: dict[str, list[dict[str, object]]],
    task_ids: list[str],
    sweeps_values: tuple[int, ...],
    rhos: tuple[float, ...],
    n_sim: int,
    bootstrap_resamples: int,
) -> list[dict[str, object]]:
    total_sweeps = schedule.get("sweeps")
    if not isinstance(total_sweeps, int) or max(sweeps_values) > total_sweeps:
        raise ProofViolation("schedule-does-not-cover-requested-sweeps")
    rates = {engine: centered_profile(engine, task_ids) for engine in ENGINES}
    return [
        summarize_cell(scenario, rho, sweeps, sessions_by_replicate, rates, n_sim, bootstrap_resamples)
        for sweeps in sweeps_values
        for rho in rhos
        for scenario in SCENARIOS
    ]


def self_test() -> None:
    assert select_terminal((0.3, 0.4), False) == "CONFIRMED"
    assert select_terminal((0.0, 0.1), False) == "MATERIAL_GAP_REFUTED"
    assert select_terminal((DELTA_H, DELTA_H), False) == "INCONCLUSIVE_AT_PILOT_N"
    assert select_terminal((0.3, 0.4), True) == "SATURATED"
    pairs = {
        "claude-opus-5": {"t": (0.0, 1.0)},
        "claude-opus-4-8": {"t": (1.0, 0.0)},
    }
    assert complete_replicate_interaction(pairs) == 2.0
    assert non_tied_pair_count(pairs["claude-opus-5"]) == 1
    assert decision_path([0.3, 0.3], False, 100)[2] == "CONFIRMED"
    assert bootstrap_ci([0.0, 0.0, 0.0, 0.0], 100)[0] == 0.0
    assert draw_failure_fraction(0.0, 0.0, 0.5, random.Random(1)) == 0.0
    assert draw_failure_fraction(1.0, 0.0, 0.5, random.Random(1)) == 1.0
    print("PASS g0-power-0112 self-test: strict terminals, saturated precedence, bootstrap, degenerate fractions, non-tied support")


def print_criteria(criteria: list[dict[str, object]]) -> None:
    for entry in criteria:
        for name, criterion in entry["criteria"].items():
            state = "PASS" if criterion["passed"] else "FAIL"
            print(f"{state} G0 {name} S={entry['sweeps']}: {criterion['value']:.4f} {criterion['required']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE)
    parser.add_argument("--n-sim", type=int, default=DEFAULT_N_SIM)
    parser.add_argument("--bootstrap-resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    parser.add_argument(
        "--search-max-sweeps",
        type=int,
        default=None,
        help="extend the mandatory S=1,2 grid through this S; defaults to the schedule's S",
    )
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        if args.n_sim < DEFAULT_N_SIM:
            raise ProofViolation("n-sim-must-be-at-least-2000")
        if args.bootstrap_resamples < 200:
            raise ProofViolation("bootstrap-resamples-must-be-at-least-200")
        schedule, sessions_by_replicate, task_ids = parse_schedule(args.schedule)
        primary = run_grid(
            schedule, sessions_by_replicate, task_ids, (1, 2), RHO_MEMBERS, args.n_sim, args.bootstrap_resamples
        )
        criteria = [criteria_for_s(primary, sweeps) for sweeps in (1, 2)]
        escalation: list[dict[str, object]] = []
        search_max_sweeps = schedule["sweeps"] if args.search_max_sweeps is None else args.search_max_sweeps
        for sweeps in range(3, search_max_sweeps + 1):
            if any(item["passed"] for item in criteria):
                break
            cells = run_grid(
                schedule, sessions_by_replicate, task_ids, (sweeps,), RHO_MEMBERS, args.n_sim, args.bootstrap_resamples
            )
            escalation.extend(cells)
            criteria.append(criteria_for_s(cells, sweeps))
        passing = [int(item["sweeps"]) for item in criteria if item["passed"]]
        result = {
            "schema": "iter0112-g0-power-proof-v1",
            "schedule": str(args.schedule),
            "schedule_sha256": hashlib.sha256(args.schedule.read_bytes()).hexdigest(),
            "seed": SEED,
            "n_sim": args.n_sim,
            "bootstrap": {
                "unit": "complete_block_crossover_replicate",
                "resamples": args.bootstrap_resamples,
                "seed": BOOTSTRAP_SEED,
                "method": "percentile bootstrap; local reimplementation of the 0103 strict-bound decision path",
            },
            "decision": {
                "estimand": "mean_t,r((late-early)_opus5-(late-early)_opus48)",
                "delta_h": DELTA_H,
                "terminals": ["CONFIRMED", "MATERIAL_GAP_REFUTED", "INCONCLUSIVE_AT_PILOT_N", "SATURATED"],
                "saturated_definition": "all matrix-engine LATE task fractions equal 1 in every deciding replicate; SATURATED precedes CI terminals",
            },
            "assumptions": {
                "marginal_anchors": ANCHORS,
                "per_task_heterogeneity": {
                    "shape": "centered deterministic Gaussian profile",
                    "spread_sd": HETEROGENEITY_SPREAD,
                    "preserves_anchor_mean_exactly": True,
                },
                "correlation_envelope": {
                    "members": list(RHO_MEMBERS),
                    "model": "Gaussian-copula threshold with a shared session-level latent normal shock",
                    "rho_interpretation": "latent within-session equicorrelation; every registered member is evaluated and each criterion uses its empirical worst member",
                },
                "outcome_proxy": "Bernoulli manifestation-fail fraction per task, the maximum-variance [0,1] proxy consistent with published means only",
            },
            "cells": primary,
            "escalation_cells": escalation,
            "criteria_by_sweeps": criteria,
            "chosen_sweeps": min(passing) if passing else None,
        }
        print_criteria(criteria)
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0 if passing else 1
    except ProofViolation as exc:
        print(f"FAIL g0-power-0112: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
