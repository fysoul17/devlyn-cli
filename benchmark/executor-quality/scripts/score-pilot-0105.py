#!/usr/bin/env python3
"""Score the executor-quality pre-corpus mechanism pilot ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path


ENGINE = "claude-sonnet-5"
REPS = {1, 2}
PILOT_TASKS = {"EQ4P-UA1", "EQ4P-MI1", "EQ4P-AF1", "EQ4P-BD1"}
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


class ExitThreeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"decision": "UNSCORED", "reasons": [f"argument: {message}"]}, sort_keys=True))
        raise SystemExit(3)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def fraction_string(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


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

    fields = set(row)
    if not REQUIRED_ROW_FIELDS <= fields or fields - REQUIRED_ROW_FIELDS - OPTIONAL_ROW_FIELDS:
        return [f"{label}: fields differ from frozen ledger schema"]

    errors: list[str] = []
    for key in ("run_id", "task", "engine_requested"):
        if not isinstance(row[key], str) or not row[key]:
            errors.append(f"{label}: {key} must be a non-empty string")
    if row["engine_requested"] != ENGINE:
        errors.append(f"{label}: engine_requested must be {ENGINE}")

    attested = row["engine_attested"]
    if attested is not None and not isinstance(attested, str):
        errors.append(f"{label}: engine_attested must be a string or null")
    if isinstance(attested, str) and attested and attested != row["engine_requested"]:
        errors.append(f"{label}: attestation requested and attested engines differ")

    if "prompt_sha256" in row and (
        not isinstance(row["prompt_sha256"], str)
        or len(row["prompt_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in row["prompt_sha256"])
    ):
        errors.append(f"{label}: prompt_sha256 must be a lowercase SHA-256 digest")
    if isinstance(row["task"], str) and row["task"] not in PILOT_TASKS:
        errors.append(f"{label}: task is not in the pilot task set")
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
    if (attested is None or attested == "") and (
        type(row["catastrophic"]) is not bool or not row["catastrophic"]
    ):
        errors.append(f"{label}: empty engine_attested requires catastrophic")
    if type(row["wall_ms"]) is not int or row["wall_ms"] < 0:
        errors.append(f"{label}: wall_ms must be a non-negative integer")

    flagged = type(row["catastrophic"]) is bool and type(row["incomplete"]) is bool and (
        row["catastrophic"] or row["incomplete"]
    )
    if type(total) is int and not flagged and total != 5:
        errors.append(f"{label}: non-flag rows require manifestations_total of 5")
    return errors


def validity_errors(rows: list[object]) -> list[str]:
    errors: list[str] = []
    if len(rows) != 8:
        errors.append(f"row_count: expected 8, got {len(rows)}")
    for index, row in enumerate(rows, 1):
        errors.extend(validate_row(row, index))
    if errors:
        return errors

    typed_rows = [row for row in rows if isinstance(row, dict)]
    tasks = {str(row["task"]) for row in typed_rows}
    if tasks != PILOT_TASKS:
        errors.append(f"tasks: expected pilot task set, got {sorted(tasks)}")
    run_ids = [str(row["run_id"]) for row in typed_rows]
    if len(set(run_ids)) != len(run_ids):
        errors.append("run_id: values must be unique")
    cells = [(row["task"], row["rep"]) for row in typed_rows]
    if len(set(cells)) != len(cells):
        errors.append("cells: duplicate task/rep row")
    expected_cells = {(task, rep) for task in PILOT_TASKS for rep in REPS}
    if set(cells) != expected_cells:
        errors.append("cells: ledger is not a complete task x 2-rep matrix")
    for row in typed_rows:
        if row["infra_invalid"]:
            errors.append(f"infra_invalid: {row['run_id']}")
    return errors


def score_valid(rows: list[dict[str, object]], ledger_sha256: str) -> dict[str, object]:
    failures: dict[str, list[Fraction]] = {}
    for row in rows:
        failure = (
            Fraction(1)
            if row["catastrophic"] or row["incomplete"]
            else Fraction(int(row["manifestations_failed"]), int(row["manifestations_total"]))
        )
        failures.setdefault(str(row["task"]), []).append(failure)

    q_pilot = {
        task: sum(failures[task], Fraction()) / len(failures[task])
        for task in sorted(failures)
    }
    mean = sum(q_pilot.values(), Fraction()) / len(q_pilot)
    interior_count = sum(0 < value < 1 for value in q_pilot.values())
    has_total_failure = any(value == 1 for value in q_pilot.values())
    proceed = (
        Fraction(1, 10) <= mean <= Fraction(3, 5)
        and interior_count >= 3
        and not has_total_failure
    )
    return {
        "decision": "PROCEED" if proceed else "REJECT",
        "engine": ENGINE,
        "ledger_sha256": ledger_sha256,
        "mean": fraction_string(mean),
        "q_pilot": {task: fraction_string(value) for task, value in q_pilot.items()},
    }


def evaluate(path: Path) -> tuple[dict[str, object], int]:
    rows, raw, errors = load_ledger(path)
    errors.extend(validity_errors(rows))
    digest = hashlib.sha256(raw).hexdigest()
    if errors:
        return {
            "decision": "UNSCORED",
            "engine": ENGINE,
            "ledger_sha256": digest,
            "reasons": sorted(set(errors)),
        }, 3
    verdict = score_valid([row for row in rows if isinstance(row, dict)], digest)
    return verdict, 0 if verdict["decision"] == "PROCEED" else 2


def synthetic_rows(q_values: list[Fraction]) -> list[dict[str, object]]:
    tasks = sorted(PILOT_TASKS)
    if len(q_values) != len(tasks):
        raise ValueError(f"synthetic rows require {len(tasks)} q values")

    rows: list[dict[str, object]] = []
    for task, q_value in zip(tasks, q_values, strict=True):
        failed_sum = q_value * 10
        if failed_sum.denominator != 1 or not 0 <= failed_sum <= 10:
            raise ValueError(f"synthetic q value is not representable in two five-manifestation reps: {q_value}")
        first_failed = min(int(failed_sum), 5)
        second_failed = int(failed_sum) - first_failed
        for rep, failed in ((1, first_failed), (2, second_failed)):
            rows.append(
                {
                    "run_id": f"{ENGINE}-{task}-{rep}",
                    "task": task,
                    "rep": rep,
                    "engine_requested": ENGINE,
                    "engine_attested": ENGINE,
                    "manifestations_total": 5,
                    "manifestations_failed": failed,
                    "catastrophic": False,
                    "incomplete": False,
                    "infra_invalid": False,
                    "wall_ms": 100,
                }
            )
    return rows


def write_ledger(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_bytes(b"".join(json_bytes(row) for row in rows))


def assert_verdict(
    path: Path,
    rows: list[dict[str, object]],
    expected_decision: str,
    expected_exit: int,
    expected_mean: str | None = None,
) -> dict[str, object]:
    write_ledger(path, rows)
    verdict, exit_code = evaluate(path)
    if (
        exit_code != expected_exit
        or verdict["decision"] != expected_decision
        or (expected_mean is not None and verdict.get("mean") != expected_mean)
    ):
        raise AssertionError(f"{path.stem} produced {verdict} with exit {exit_code}")
    return verdict


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="executor-quality-pilot-") as temporary:
        root = Path(temporary)
        proceed_rows = synthetic_rows([Fraction(1, 5)] * 4)
        assert_verdict(root / "a-proceed.jsonl", proceed_rows, "PROCEED", 0, "1/5")
        assert_verdict(root / "b-mean-below.jsonl", synthetic_rows([Fraction(0)] * 4), "REJECT", 2, "0/1")
        assert_verdict(root / "c-mean-above.jsonl", synthetic_rows([Fraction(4, 5)] * 4), "REJECT", 2, "4/5")

        interior_two = [Fraction(0), Fraction(0), Fraction(1, 5), Fraction(1, 5)]
        assert_verdict(root / "d-interior-two.jsonl", synthetic_rows(interior_two), "REJECT", 2, "1/10")
        one_total = [Fraction(1), Fraction(1, 5), Fraction(1, 5), Fraction(1, 5)]
        assert_verdict(root / "e-total-prototype.jsonl", synthetic_rows(one_total), "REJECT", 2, "2/5")

        infra_rows = synthetic_rows([Fraction(1, 5)] * 4)
        infra_rows[0]["infra_invalid"] = True
        assert_verdict(root / "f-infra-invalid.jsonl", infra_rows, "UNSCORED", 3)

        assert_verdict(root / "g-wrong-count.jsonl", proceed_rows[:-1], "UNSCORED", 3)
        wrong_task_rows = synthetic_rows([Fraction(1, 5)] * 4)
        wrong_task_rows[0]["task"] = "EQ4P-WRONG"
        assert_verdict(root / "g-wrong-task.jsonl", wrong_task_rows, "UNSCORED", 3)
        duplicate_rows = synthetic_rows([Fraction(1, 5)] * 4)
        duplicate_rows[1]["run_id"] = duplicate_rows[0]["run_id"]
        assert_verdict(root / "g-duplicate-run-id.jsonl", duplicate_rows, "UNSCORED", 3)

        catastrophic_rows = synthetic_rows([Fraction(1, 5)] * 4)
        catastrophic_task = str(catastrophic_rows[0]["task"])
        catastrophic_rows[0].update(
            {
                "engine_attested": None,
                "manifestations_total": 0,
                "manifestations_failed": 0,
                "catastrophic": True,
            }
        )
        catastrophic = assert_verdict(root / "h-catastrophic.jsonl", catastrophic_rows, "PROCEED", 0, "11/40")
        if catastrophic["q_pilot"][catastrophic_task] != "1/2":
            raise AssertionError(f"catastrophic row was not scored as f=1: {catastrophic}")

        extra_field_rows = synthetic_rows([Fraction(1, 5)] * 4)
        extra_field_rows[0]["driver_sha256"] = "0" * 64
        assert_verdict(root / "i-extra-field.jsonl", extra_field_rows, "UNSCORED", 3)

        deterministic = root / "j-deterministic.jsonl"
        write_ledger(deterministic, proceed_rows)
        first, first_exit = evaluate(deterministic)
        second, second_exit = evaluate(deterministic)
        if first_exit != second_exit or json_bytes(first) != json_bytes(second):
            raise AssertionError("two pilot verdicts were not byte-identical")

        assert_verdict(root / "k-lower-boundary.jsonl", synthetic_rows([Fraction(1, 10)] * 4), "PROCEED", 0, "1/10")
        assert_verdict(root / "k-upper-boundary.jsonl", synthetic_rows([Fraction(3, 5)] * 4), "PROCEED", 0, "3/5")

        bad_total_rows = synthetic_rows([Fraction(1, 5)] * 4)
        bad_total_rows[0]["manifestations_total"] = 4
        bad_total_rows[0]["manifestations_failed"] = 1
        assert_verdict(root / "l-non-five-total.jsonl", bad_total_rows, "UNSCORED", 3)


def main() -> int:
    parser = ExitThreeParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ledger", type=Path)
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (AssertionError, OSError, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 1
        print("SELF_TEST_OK: 12 pilot decision, validity, exact-fraction, and determinism scenarios")
        return 0
    verdict, exit_code = evaluate(args.ledger)
    sys.stdout.buffer.write(json_bytes(verdict))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
