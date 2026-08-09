#!/usr/bin/env python3
"""Score the frozen executor-quality single-engine calibration ledger."""

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
FROZEN_TASKS = {
    f"EQ2-{prefix}{index}"
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


class ExitThreeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"band": "UNSCORED", "reasons": [f"argument: {message}"]}, sort_keys=True))
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
    if isinstance(row["task"], str) and row["task"] not in FROZEN_TASKS:
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
    if (attested is None or attested == "") and (
        type(row["catastrophic"]) is not bool or not row["catastrophic"]
    ):
        errors.append(f"{label}: empty engine_attested requires catastrophic")
    if type(row["wall_ms"]) is not int or row["wall_ms"] < 0:
        errors.append(f"{label}: wall_ms must be a non-negative integer")
    return errors


def validity_errors(rows: list[object]) -> list[str]:
    errors: list[str] = []
    if len(rows) != 64:
        errors.append(f"row_count: expected 64, got {len(rows)}")
    for index, row in enumerate(rows, 1):
        errors.extend(validate_row(row, index))
    if errors:
        return errors

    typed_rows = [row for row in rows if isinstance(row, dict)]
    tasks = {str(row["task"]) for row in typed_rows}
    if tasks != FROZEN_TASKS:
        errors.append(f"tasks: expected frozen task set, got {sorted(tasks)}")
    run_ids = [str(row["run_id"]) for row in typed_rows]
    if len(set(run_ids)) != len(run_ids):
        errors.append("run_id: values must be unique")
    cells = [(row["task"], row["rep"]) for row in typed_rows]
    if len(set(cells)) != len(cells):
        errors.append("cells: duplicate task/rep row")
    expected_cells = {(task, rep) for task in FROZEN_TASKS for rep in REPS}
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

    q_cal = {
        task: sum(failures[task], Fraction()) / len(failures[task])
        for task in sorted(failures)
    }
    sorted_q = sorted(q_cal.values())
    mean = sum(sorted_q, Fraction()) / len(sorted_q)
    median = (sorted_q[15] + sorted_q[16]) / 2
    interior_count = sum(0 < value < 1 for value in sorted_q)
    total_fail_count = sum(value == 1 for value in sorted_q)
    passed = (
        Fraction(1, 5) <= mean <= Fraction(3, 5)
        and Fraction(1, 5) <= median <= Fraction(3, 5)
        and interior_count >= 22
        and total_fail_count <= 2
    )
    return {
        "band": "PASS" if passed else "MISS",
        "engine": ENGINE,
        "interior_count": interior_count,
        "ledger_sha256": ledger_sha256,
        "mean": fraction_string(mean),
        "median": fraction_string(median),
        "q_cal": {task: fraction_string(value) for task, value in q_cal.items()},
        "total_fail_count": total_fail_count,
    }


def evaluate(path: Path) -> tuple[dict[str, object], int]:
    rows, raw, errors = load_ledger(path)
    errors.extend(validity_errors(rows))
    digest = hashlib.sha256(raw).hexdigest()
    if errors:
        return {
            "band": "UNSCORED",
            "engine": ENGINE,
            "ledger_sha256": digest,
            "reasons": sorted(set(errors)),
        }, 3
    verdict = score_valid([row for row in rows if isinstance(row, dict)], digest)
    return verdict, 0 if verdict["band"] == "PASS" else 2


def synthetic_rows(q_values: list[Fraction]) -> list[dict[str, object]]:
    tasks = sorted(FROZEN_TASKS)
    if len(q_values) != len(tasks):
        raise ValueError(f"synthetic rows require {len(tasks)} q values")
    rows: list[dict[str, object]] = []
    for task, q_value in zip(tasks, q_values, strict=True):
        failed = q_value * 20
        if failed.denominator != 1:
            raise ValueError(f"synthetic q value is not representable in twentieths: {q_value}")
        for rep in sorted(REPS):
            rows.append(
                {
                    "run_id": f"{ENGINE}-{task}-{rep}",
                    "task": task,
                    "rep": rep,
                    "engine_requested": ENGINE,
                    "engine_attested": ENGINE,
                    "manifestations_total": 20,
                    "manifestations_failed": int(failed),
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
    controls = {
        "pass": ([Fraction(2, 5)] * 32, "PASS", "2/5", "2/5"),
        "mean-below": ([Fraction(1, 10)] * 32, "MISS", "1/10", "1/10"),
        "mean-above": ([Fraction(7, 10)] * 32, "MISS", "7/10", "7/10"),
        "median-below": (
            [Fraction(1, 10)] * 17 + [Fraction(4, 5)] * 15,
            "MISS",
            "137/320",
            "1/10",
        ),
        "median-above": (
            [Fraction(1, 10)] * 15 + [Fraction(7, 10)] * 17,
            "MISS",
            "67/160",
            "7/10",
        ),
        "interior-count": (
            [Fraction(0)] * 11 + [Fraction(3, 5)] * 21,
            "MISS",
            "63/160",
            "3/5",
        ),
        "total-fail-count": (
            [Fraction(2, 5)] * 29 + [Fraction(1)] * 3,
            "MISS",
            "73/160",
            "2/5",
        ),
    }
    with tempfile.TemporaryDirectory(prefix="executor-quality-calibration-") as temporary:
        root = Path(temporary)
        verdicts: dict[str, dict[str, object]] = {}
        for name, (values, expected_band, expected_mean, expected_median) in controls.items():
            ledger = root / f"{name}.jsonl"
            write_ledger(ledger, synthetic_rows(values))
            verdict, exit_code = evaluate(ledger)
            expected_exit = 0 if expected_band == "PASS" else 2
            if (
                exit_code != expected_exit
                or verdict["band"] != expected_band
                or verdict["mean"] != expected_mean
                or verdict["median"] != expected_median
            ):
                raise AssertionError(f"{name} control produced {verdict}")
            verdicts[name] = verdict

        if verdicts["median-below"]["interior_count"] != 32:
            raise AssertionError("median-below control did not isolate the median conjunct")
        if verdicts["median-above"]["interior_count"] != 32:
            raise AssertionError("median-above control did not isolate the median conjunct")
        if verdicts["interior-count"]["interior_count"] != 21:
            raise AssertionError("interior-count control did not cross the required boundary")
        if verdicts["total-fail-count"]["total_fail_count"] != 3:
            raise AssertionError("total-fail-count control did not cross the required boundary")

        infra_invalid = root / "infra-invalid.jsonl"
        infra_rows = synthetic_rows([Fraction(2, 5)] * 32)
        infra_rows[0]["infra_invalid"] = True
        write_ledger(infra_invalid, infra_rows)
        verdict, exit_code = evaluate(infra_invalid)
        if exit_code != 3 or verdict["band"] != "UNSCORED":
            raise AssertionError("infra-invalid ledger was not UNSCORED")

        deterministic = root / "deterministic.jsonl"
        write_ledger(deterministic, synthetic_rows([Fraction(2, 5)] * 32))
        first, first_exit = evaluate(deterministic)
        second, second_exit = evaluate(deterministic)
        if first_exit != second_exit or json_bytes(first) != json_bytes(second):
            raise AssertionError("two calibration verdicts were not byte-identical")

        catastrophic = root / "catastrophic.jsonl"
        catastrophic_rows = synthetic_rows([Fraction(2, 5)] * 32)
        catastrophic_task = str(catastrophic_rows[0]["task"])
        catastrophic_rows[0].update(
            {
                "engine_attested": None,
                "manifestations_total": 0,
                "manifestations_failed": 0,
                "catastrophic": True,
            }
        )
        write_ledger(catastrophic, catastrophic_rows)
        verdict, exit_code = evaluate(catastrophic)
        if (
            exit_code != 0
            or verdict["band"] != "PASS"
            or verdict["q_cal"][catastrophic_task] != "7/10"
        ):
            raise AssertionError(f"catastrophic zero-total row was not scored as f=1: {verdict}")


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
        print("SELF_TEST_OK: 10 calibration band, validity, exact-fraction, and determinism scenarios")
        return 0
    verdict, exit_code = evaluate(args.ledger)
    sys.stdout.buffer.write(json_bytes(verdict))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
