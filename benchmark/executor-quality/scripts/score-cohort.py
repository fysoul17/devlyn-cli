#!/usr/bin/env python3
"""Score the frozen executor-quality paired cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import tempfile
from pathlib import Path


SEED = 20260809
RESAMPLES = 100_000
REPS = {1, 2}
ENGINES = ("claude-opus-5", "claude-fable-5")
ROW_FIELDS = {
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
    pieces = task.split("-")
    if len(pieces) != 2 or not pieces[1]:
        return None
    prefix = "".join(character for character in pieces[1] if character.isalpha())
    suffix = pieces[1][len(prefix) :]
    if prefix not in TASK_CLASSES or not suffix.isdigit() or int(suffix) < 1:
        return None
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
    if set(row) != ROW_FIELDS:
        errors.append(f"{label}: fields differ from frozen ledger schema")
        return errors
    for key in ("run_id", "task", "engine_requested", "engine_attested"):
        if not isinstance(row[key], str) or not row[key]:
            errors.append(f"{label}: {key} must be a non-empty string")
    if isinstance(row["task"], str) and task_class(row["task"]) is None:
        errors.append(f"{label}: task must match EQ-(UA|MI|BD|AF)<positive integer>")
    if type(row["rep"]) is not int or row["rep"] not in REPS:
        errors.append(f"{label}: rep must be 1 or 2")
    total = row["manifestations_total"]
    failed = row["manifestations_failed"]
    if type(total) is not int or total <= 0:
        errors.append(f"{label}: manifestations_total must be a positive integer")
    if type(failed) is not int or type(total) is not int or failed < 0 or failed > total:
        errors.append(f"{label}: manifestations_failed must be an integer in [0,total]")
    for key in ("catastrophic", "incomplete", "infra_invalid"):
        if type(row[key]) is not bool:
            errors.append(f"{label}: {key} must be boolean")
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
    if len(tasks) != expected_tasks:
        errors.append(f"tasks: expected {expected_tasks} unique tasks, got {len(tasks)}")
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
        if row["engine_attested"] != row["engine_requested"]:
            errors.append(f"attestation: {row['run_id']} requested and attested engines differ")
        if row["infra_invalid"]:
            errors.append(f"infra_invalid: {row['run_id']}")
    return errors


def percentile(sorted_values: list[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def bootstrap_ci(differences: list[float]) -> list[float]:
    rng = random.Random(SEED)
    count = len(differences)
    samples = [
        sum(differences[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(RESAMPLES)
    ]
    samples.sort()
    return [percentile(samples, 0.025), percentile(samples, 0.975)]


def score_valid(rows: list[dict[str, object]], ledger_sha256: str) -> dict[str, object]:
    failures: dict[tuple[str, str], list[float]] = {}
    completed: dict[str, int] = {engine: 0 for engine in ENGINES}
    clean: dict[str, int] = {engine: 0 for engine in ENGINES}
    for row in rows:
        engine = str(row["engine_requested"])
        task = str(row["task"])
        is_complete = not row["catastrophic"] and not row["incomplete"]
        if is_complete:
            completed[engine] += 1
        failure = (
            1.0
            if not is_complete
            else int(row["manifestations_failed"]) / int(row["manifestations_total"])
        )
        if failure == 0.0:
            clean[engine] += 1
        failures.setdefault((engine, task), []).append(failure)
    tasks = sorted({task for _, task in failures})
    q = {
        engine: {task: sum(failures[(engine, task)]) / 2 for task in tasks}
        for engine in ENGINES
    }
    rates = {engine: sum(q[engine].values()) / len(tasks) for engine in ENGINES}
    differences = {task: q[ENGINES[0]][task] - q[ENGINES[1]][task] for task in tasks}
    delta = sum(differences.values()) / len(tasks)
    ci = bootstrap_ci(list(differences.values()))
    run_count = len(tasks) * 2
    if all(clean[engine] >= run_count - 1 for engine in ENGINES):
        terminal = "SATURATED"
    elif ci[0] > 0.15:
        terminal = "H1_CONFIRMED"
    elif ci[1] < 0.15:
        terminal = "H1_MATERIAL_GAP_REFUTED"
    else:
        terminal = "INCONCLUSIVE_AT_PILOT_N"
    failed_by_class = {
        engine: {
            class_name: sum(
                1 for task in tasks if task_class(task) == class_name and q[engine][task] > 0.0
            )
            for class_name in sorted(TASK_CLASSES.values())
        }
        for engine in ENGINES
    }
    return {
        "R": rates,
        "ci": ci,
        "completion_rate": {engine: completed[engine] / run_count for engine in ENGINES},
        "delta": delta,
        "failed_tasks_by_class": failed_by_class,
        "ledger_sha256": ledger_sha256,
        "per_task_d": differences,
        "resamples": RESAMPLES,
        "seed": SEED,
        "terminal": terminal,
    }


def evaluate(path: Path, expected_tasks: int) -> tuple[dict[str, object], int]:
    rows, raw, errors = load_ledger(path)
    if expected_tasks < 1:
        errors.append("expected_tasks: must be a positive integer")
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


def synthetic_rows(differences: list[float]) -> list[dict[str, object]]:
    prefixes = ("UA", "MI", "BD", "AF")
    rows: list[dict[str, object]] = []
    for task_index, difference in enumerate(differences, 1):
        task = f"EQ-{prefixes[(task_index - 1) % len(prefixes)]}{task_index}"
        opus_failed = round(difference * 20)
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
    scenarios = {
        "SATURATED": [0.0, 0.0, 0.0, 0.0],
        "H1_CONFIRMED": [0.5, 0.5, 0.5, 0.5],
        "H1_MATERIAL_GAP_REFUTED": [0.1, 0.1, 0.1, 0.1],
        "INCONCLUSIVE_AT_PILOT_N": [0.0, 0.0, 0.4, 0.4],
    }
    with tempfile.TemporaryDirectory(prefix="executor-quality-scorer-") as temporary:
        root = Path(temporary)
        verdicts: dict[str, dict[str, object]] = {}
        for expected_terminal, differences in scenarios.items():
            ledger = root / f"{expected_terminal}.jsonl"
            write_ledger(ledger, synthetic_rows(differences))
            verdict, exit_code = evaluate(ledger, len(differences))
            if exit_code != 0 or verdict["terminal"] != expected_terminal:
                raise AssertionError(f"{expected_terminal} scenario produced {verdict}")
            verdicts[expected_terminal] = verdict

        bad = root / "bad.jsonl"
        bad_rows = synthetic_rows([0.5, 0.5, 0.5, 0.5])
        bad_rows[0]["infra_invalid"] = True
        write_ledger(bad, bad_rows)
        verdict, exit_code = evaluate(bad, 4)
        if exit_code != 3 or verdict["terminal"] != "UNSCORED":
            raise AssertionError("infra-invalid ledger was not UNSCORED")

        mismatch = root / "mismatch.jsonl"
        mismatch_rows = synthetic_rows([0.5, 0.5, 0.5, 0.5])
        mismatch_rows[0]["engine_attested"] = ENGINES[1]
        write_ledger(mismatch, mismatch_rows)
        verdict, exit_code = evaluate(mismatch, 4)
        if exit_code != 3 or not any("attestation" in reason for reason in verdict["reasons"]):
            raise AssertionError("attestation mismatch was not rejected")

        deterministic = root / "deterministic.jsonl"
        write_ledger(deterministic, synthetic_rows(scenarios["INCONCLUSIVE_AT_PILOT_N"]))
        first, first_exit = evaluate(deterministic, 4)
        second, second_exit = evaluate(deterministic, 4)
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
    parser.add_argument("--expected-tasks", type=int, default=12)
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (AssertionError, OSError, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 1
        print("SELF_TEST_OK: 4 terminals, UNSCORED, attestation rejection, determinism, controls")
        return 0
    verdict, exit_code = evaluate(args.ledger, args.expected_tasks)
    sys.stdout.buffer.write(json_bytes(verdict))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
