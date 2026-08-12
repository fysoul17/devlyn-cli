#!/usr/bin/env python3
"""Score the frozen executor-quality paired cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import tempfile
from fractions import Fraction
from pathlib import Path


SEED = 20260809
RESAMPLES = 100_000
REPS = {1, 2}
ENGINES = ("claude-opus-5", "claude-fable-5")
FROZEN_TASKS = {
    f"EQ3-{prefix}{index}"
    for prefix in ("UA", "MI", "AF", "BD")
    for index in range(1, 9)
}
REQUIRED_ROW_FIELDS = {
    "run_id",
    "task",
    "rep",
    "engine_requested",
    "engine_attested",
    "manifestations_total",
    "manifestations_failed",
    "catastrophic",
    "incomplete",
    "infra_invalid",
    "wall_ms",
}
OPTIONAL_ROW_FIELDS = {"prompt_sha256"}
TASK_CLASSES = {
    "UA": "unsupported_assumption",
    "MI": "missed_repo_invariant",
    "BD": "broken_dependency",
    "AF": "absent_failure_mode",
}


class ExitThreeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"reasons": [f"argument: {message}"], "terminal": "UNSCORED"}, sort_keys=True))
        raise SystemExit(3)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def task_class(task: str) -> str | None:
    if task not in FROZEN_TASKS:
        return None
    pieces = task.split("-")
    prefix = "".join(character for character in pieces[1] if character.isalpha())
    return TASK_CLASSES[prefix]


def load_ledger(path: Path) -> tuple[list[object], bytes, list[str]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [], b"", [f"ledger: cannot read {path}: {exc}"]
    rows: list[object] = []
    errors: list[str] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            errors.append(f"ledger line {line_number}: blank lines are not allowed")
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"ledger line {line_number}: invalid JSON: {exc.msg}")
    return rows, raw, errors


def validate_row(row: object, index: int) -> list[str]:
    label = f"row {index}"
    if not isinstance(row, dict):
        return [f"{label}: must be an object"]
    errors: list[str] = []
    fields = set(row)
    if not REQUIRED_ROW_FIELDS <= fields or fields - REQUIRED_ROW_FIELDS - OPTIONAL_ROW_FIELDS:
        errors.append(f"{label}: fields differ from frozen ledger schema")
        return errors
    for key in ("run_id", "task", "engine_requested"):
        if not isinstance(row[key], str) or not row[key]:
            errors.append(f"{label}: {key} must be a non-empty string")
    attested = row["engine_attested"]
    if attested is not None and not isinstance(attested, str):
        errors.append(f"{label}: engine_attested must be a string or null")
    if "prompt_sha256" in row and (
        not isinstance(row["prompt_sha256"], str)
        or len(row["prompt_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in row["prompt_sha256"])
    ):
        errors.append(f"{label}: prompt_sha256 must be a lowercase SHA-256 digest")
    if isinstance(row["task"], str) and task_class(row["task"]) is None:
        errors.append(f"{label}: task is not in the frozen task set")
    if type(row["rep"]) is not int or row["rep"] not in REPS:
        errors.append(f"{label}: rep must be 1 or 2")
    total = row["manifestations_total"]
    failed = row["manifestations_failed"]
    if type(total) is not int or total < 0:
        errors.append(f"{label}: manifestations_total must be a non-negative integer")
    if type(failed) is not int or type(total) is not int or failed < 0 or failed > total:
        errors.append(f"{label}: manifestations_failed must be an integer in [0,total]")
    for key in ("catastrophic", "incomplete", "infra_invalid"):
        if type(row[key]) is not bool:
            errors.append(f"{label}: {key} must be boolean")
    flags_are_boolean = all(type(row[key]) is bool for key in ("catastrophic", "incomplete"))
    if type(total) is int and total == 0 and flags_are_boolean and not (
        row["catastrophic"] or row["incomplete"]
    ):
        errors.append(f"{label}: zero manifestations require catastrophic or incomplete")
    if isinstance(attested, str) and attested and attested != row["engine_requested"]:
        errors.append(f"{label}: attestation requested and attested engines differ")
    if (attested is None or attested == "") and (
        type(row["catastrophic"]) is not bool or not row["catastrophic"]
    ):
        errors.append(f"{label}: empty engine_attested requires catastrophic")
    if type(row["wall_ms"]) is not int or row["wall_ms"] < 0:
        errors.append(f"{label}: wall_ms must be a non-negative integer")
    return errors


def validity_errors(rows: list[object], expected_tasks: int) -> list[str]:
    errors: list[str] = []
    expected_rows = 2 * expected_tasks * 2
    if len(rows) != expected_rows:
        errors.append(f"row_count: expected {expected_rows}, got {len(rows)}")
    for index, row in enumerate(rows, 1):
        errors.extend(validate_row(row, index))
    if errors:
        return errors
    typed_rows = [row for row in rows if isinstance(row, dict)]
    engines = {str(row["engine_requested"]) for row in typed_rows}
    if engines != set(ENGINES):
        errors.append(f"engines: expected {list(ENGINES)}, got {sorted(engines)}")
    tasks = {str(row["task"]) for row in typed_rows}
    if tasks != FROZEN_TASKS:
        errors.append(f"tasks: expected frozen task set, got {sorted(tasks)}")
    run_ids = [str(row["run_id"]) for row in typed_rows]
    if len(set(run_ids)) != len(run_ids):
        errors.append("run_id: values must be unique")
    cells = [(row["engine_requested"], row["task"], row["rep"]) for row in typed_rows]
    if len(set(cells)) != len(cells):
        errors.append("cells: duplicate engine/task/rep row")
    expected_cells = {(engine, task, rep) for engine in ENGINES for task in tasks for rep in REPS}
    if set(cells) != expected_cells:
        errors.append("cells: ledger is not a complete 2-engine x task x 2-rep matrix")
    for row in typed_rows:
        if row["infra_invalid"]:
            errors.append(f"infra_invalid: {row['run_id']}")
    return errors


def percentile(sorted_values: list[Fraction], probability: Fraction) -> Fraction:
    position = probability * (len(sorted_values) - 1)
    lower = position.numerator // position.denominator
    upper = -(-position.numerator // position.denominator)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def bootstrap_ci(differences: list[Fraction]) -> list[Fraction]:
    rng = random.Random(SEED)
    count = len(differences)
    samples = [
        sum((differences[rng.randrange(count)] for _ in range(count)), Fraction()) / count
        for _ in range(RESAMPLES)
    ]
    samples.sort()
    return [percentile(samples, Fraction(1, 40)), percentile(samples, Fraction(39, 40))]


def select_terminal(clean: dict[str, int], run_count: int, ci: list[Fraction]) -> str:
    threshold = Fraction(3, 20)
    if all(clean[engine] >= run_count - 1 for engine in ENGINES):
        return "SATURATED"
    if ci[0] > threshold:
        return "H1_CONFIRMED"
    if ci[1] < threshold:
        return "H1_MATERIAL_GAP_REFUTED"
    return "INCONCLUSIVE_AT_PILOT_N"


def score_valid(rows: list[dict[str, object]], ledger_sha256: str) -> dict[str, object]:
    failures: dict[tuple[str, str], list[Fraction]] = {}
    completed: dict[str, int] = {engine: 0 for engine in ENGINES}
    clean: dict[str, int] = {engine: 0 for engine in ENGINES}
    for row in rows:
        engine = str(row["engine_requested"])
        task = str(row["task"])
        is_complete = not row["catastrophic"] and not row["incomplete"]
        if is_complete:
            completed[engine] += 1
        failure = (
            Fraction(1)
            if not is_complete
            else Fraction(int(row["manifestations_failed"]), int(row["manifestations_total"]))
        )
        if failure == 0:
            clean[engine] += 1
        failures.setdefault((engine, task), []).append(failure)
    tasks = sorted({task for _, task in failures})
    q = {
        engine: {
            task: sum(failures[(engine, task)], Fraction()) / len(failures[(engine, task)])
            for task in tasks
        }
        for engine in ENGINES
    }
    rates = {
        engine: sum(q[engine].values(), Fraction()) / len(tasks) for engine in ENGINES
    }
    differences = {task: q[ENGINES[0]][task] - q[ENGINES[1]][task] for task in tasks}
    delta = sum(differences.values(), Fraction()) / len(tasks)
    ci = bootstrap_ci(list(differences.values()))
    run_count = len(tasks) * 2
    terminal = select_terminal(clean, run_count, ci)
    failed_by_class = {
        engine: {
            class_name: sum(
                1 for task in tasks if task_class(task) == class_name and q[engine][task] > 0
            )
            for class_name in sorted(TASK_CLASSES.values())
        }
        for engine in ENGINES
    }
    return {
        "R": {engine: float(rates[engine]) for engine in ENGINES},
        "ci": [float(bound) for bound in ci],
        "completion_rate": {engine: completed[engine] / run_count for engine in ENGINES},
        "delta": float(delta),
        "failed_tasks_by_class": failed_by_class,
        "ledger_sha256": ledger_sha256,
        "per_task_d": {task: float(differences[task]) for task in tasks},
        "resamples": RESAMPLES,
        "seed": SEED,
        "terminal": terminal,
    }


def evaluate(path: Path, expected_tasks: int) -> tuple[dict[str, object], int]:
    rows, raw, errors = load_ledger(path)
    if expected_tasks != len(FROZEN_TASKS):
        errors.append(f"expected_tasks: must be {len(FROZEN_TASKS)}")
    else:
        errors.extend(validity_errors(rows, expected_tasks))
    digest = hashlib.sha256(raw).hexdigest()
    if errors:
        return {
            "ledger_sha256": digest,
            "reasons": sorted(set(errors)),
            "resamples": RESAMPLES,
            "seed": SEED,
            "terminal": "UNSCORED",
        }, 3
    return score_valid([row for row in rows if isinstance(row, dict)], digest), 0


def synthetic_rows(differences: list[Fraction]) -> list[dict[str, object]]:
    tasks = sorted(FROZEN_TASKS)
    if len(differences) != len(tasks):
        raise ValueError(f"synthetic rows require {len(tasks)} differences")
    rows: list[dict[str, object]] = []
    for task, difference in zip(tasks, differences, strict=True):
        opus_failed = int(difference * 20)
        for engine in ENGINES:
            for rep in sorted(REPS):
                rows.append(
                    {
                        "run_id": f"{engine}-{task}-{rep}",
                        "task": task,
                        "rep": rep,
                        "engine_requested": engine,
                        "engine_attested": engine,
                        "manifestations_total": 20,
                        "manifestations_failed": opus_failed if engine == ENGINES[0] else 0,
                        "catastrophic": False,
                        "incomplete": False,
                        "infra_invalid": False,
                        "wall_ms": 100,
                    }
                )
    return rows


def write_ledger(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_bytes(b"".join(json_bytes(row) for row in rows))


def self_test() -> None:
    task_count = len(FROZEN_TASKS)
    scenarios = {
        "SATURATED": [Fraction(0)] * task_count,
        "H1_CONFIRMED": [Fraction(1, 2)] * task_count,
        "H1_MATERIAL_GAP_REFUTED": [Fraction(1, 10)] * task_count,
        "INCONCLUSIVE_AT_PILOT_N": [Fraction(0)] * 16 + [Fraction(2, 5)] * 16,
    }
    with tempfile.TemporaryDirectory(prefix="executor-quality-scorer-") as temporary:
        root = Path(temporary)
        verdicts: dict[str, dict[str, object]] = {}
        for expected_terminal, differences in scenarios.items():
            ledger = root / f"{expected_terminal}.jsonl"
            write_ledger(ledger, synthetic_rows(differences))
            verdict, exit_code = evaluate(ledger, task_count)
            if exit_code != 0 or verdict["terminal"] != expected_terminal:
                raise AssertionError(f"{expected_terminal} scenario produced {verdict}")
            verdicts[expected_terminal] = verdict

        bad = root / "bad.jsonl"
        bad_rows = synthetic_rows([Fraction(1, 2)] * task_count)
        bad_rows[0]["infra_invalid"] = True
        write_ledger(bad, bad_rows)
        verdict, exit_code = evaluate(bad, task_count)
        if exit_code != 3 or verdict["terminal"] != "UNSCORED":
            raise AssertionError("infra-invalid ledger was not UNSCORED")

        saturated_boundary = root / "saturated-boundary.jsonl"
        saturated_boundary_rows = synthetic_rows([Fraction(0)] * task_count)
        saturated_boundary_rows[0]["manifestations_failed"] = 1
        write_ledger(saturated_boundary, saturated_boundary_rows)
        verdict, exit_code = evaluate(saturated_boundary, task_count)
        if exit_code != 0 or verdict["terminal"] != "SATURATED":
            raise AssertionError(f"63/64 clean-run boundary produced {verdict}")

        mismatch = root / "mismatch.jsonl"
        mismatch_rows = synthetic_rows([Fraction(1, 2)] * task_count)
        mismatch_rows[0]["engine_attested"] = ENGINES[1]
        write_ledger(mismatch, mismatch_rows)
        verdict, exit_code = evaluate(mismatch, task_count)
        if exit_code != 3 or not any("attestation" in reason for reason in verdict["reasons"]):
            raise AssertionError("attestation mismatch was not rejected")

        exact_boundary = root / "exact-boundary.jsonl"
        write_ledger(exact_boundary, synthetic_rows([Fraction(3, 20)] * task_count))
        verdict, exit_code = evaluate(exact_boundary, task_count)
        if (
            exit_code != 0
            or verdict["terminal"] != "INCONCLUSIVE_AT_PILOT_N"
            or verdict["delta"] != 0.15
            or verdict["ci"] != [0.15, 0.15]
        ):
            raise AssertionError(f"exact 3/20 boundary produced {verdict}")
        upper_boundary = root / "upper-boundary.jsonl"
        write_ledger(
            upper_boundary,
            synthetic_rows([Fraction(2, 5)] * 7 + [Fraction(0)] * 25),
        )
        verdict, exit_code = evaluate(upper_boundary, task_count)
        if (
            exit_code != 0
            or verdict["terminal"] != "INCONCLUSIVE_AT_PILOT_N"
            or verdict["ci"] != [0.0375, 0.15]
        ):
            raise AssertionError(f"CI upper bound equal to 3/20 produced {verdict}")

        duplicate = root / "duplicate.jsonl"
        duplicate_rows = synthetic_rows([Fraction(1, 10)] * task_count)
        duplicate_rows[1]["run_id"] = duplicate_rows[0]["run_id"]
        write_ledger(duplicate, duplicate_rows)
        verdict, exit_code = evaluate(duplicate, task_count)
        if exit_code != 3 or verdict["terminal"] != "UNSCORED":
            raise AssertionError("duplicate run_id ledger was not UNSCORED")

        catastrophic = root / "catastrophic.jsonl"
        catastrophic_rows = synthetic_rows([Fraction(1, 10)] * task_count)
        catastrophic_rows[0].update(
            {
                "engine_attested": None,
                "manifestations_total": 0,
                "manifestations_failed": 0,
                "catastrophic": True,
                "wall_ms": 300_000,
            }
        )
        write_ledger(catastrophic, catastrophic_rows)
        verdict, exit_code = evaluate(catastrophic, task_count)
        if exit_code != 0 or verdict["terminal"] == "UNSCORED" or verdict["R"][ENGINES[0]] <= 0.1:
            raise AssertionError(f"catastrophic zero-total row was not scored as f=1: {verdict}")

        substituted = root / "substituted.jsonl"
        substituted_rows = synthetic_rows([Fraction(1, 10)] * task_count)
        for row in substituted_rows:
            if row["task"] == "EQ3-UA1":
                row["task"] = "EQ3-UA99"
        write_ledger(substituted, substituted_rows)
        verdict, exit_code = evaluate(substituted, task_count)
        if exit_code != 3 or verdict["terminal"] != "UNSCORED":
            raise AssertionError("substituted task ledger was not UNSCORED")

        prompted = root / "prompted.jsonl"
        prompted_rows = synthetic_rows([Fraction(1, 10)] * task_count)
        prompted_rows[0]["prompt_sha256"] = "0" * 64
        write_ledger(prompted, prompted_rows)
        verdict, exit_code = evaluate(prompted, task_count)
        if exit_code != 0 or verdict["terminal"] == "UNSCORED":
            raise AssertionError("named optional prompt_sha256 was rejected")

        unexpected = root / "unexpected.jsonl"
        unexpected_rows = synthetic_rows([Fraction(1, 10)] * task_count)
        unexpected_rows[0]["driver_sha256"] = "0" * 64
        write_ledger(unexpected, unexpected_rows)
        verdict, exit_code = evaluate(unexpected, task_count)
        if exit_code != 3 or verdict["terminal"] != "UNSCORED":
            raise AssertionError("unexpected driver_sha256 field was not rejected")

        deterministic = root / "deterministic.jsonl"
        write_ledger(deterministic, synthetic_rows(scenarios["INCONCLUSIVE_AT_PILOT_N"]))
        first, first_exit = evaluate(deterministic, task_count)
        second, second_exit = evaluate(deterministic, task_count)
        if first_exit != second_exit or json_bytes(first) != json_bytes(second):
            raise AssertionError("two scorer runs were not byte-identical")

        bad_terminal = verdicts["H1_CONFIRMED"]["terminal"]
        if bad_terminal in {"SATURATED", "H1_MATERIAL_GAP_REFUTED"}:
            raise AssertionError("obviously bad opus synthetic control reached a good/separation-free terminal")


def main() -> int:
    parser = ExitThreeParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ledger", type=Path)
    group.add_argument("--self-test", action="store_true")
    parser.add_argument("--expected-tasks", type=int, default=32)
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (AssertionError, OSError, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 1
        print("SELF_TEST_OK: exact fractions, 4 terminals, strict boundaries, catastrophic rows, frozen tasks, attestation, determinism")
        return 0
    verdict, exit_code = evaluate(args.ledger, args.expected_tasks)
    sys.stdout.buffer.write(json_bytes(verdict))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
