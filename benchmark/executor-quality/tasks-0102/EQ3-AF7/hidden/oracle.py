#!/usr/bin/env python3
"""Evaluate the adoption fixture without writing to the supplied tree."""

from copy import deepcopy
import json
import pathlib
import sys


def load(root, relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


def regular_case(intake, outside=False):
    return intake["open_case"]("A-7", True, outside, None, "R-7", 3150)


def returned_case(intake, animal_id, hold, receipt, fee_cents):
    return intake["open_case"](animal_id, True, False, hold, receipt, fee_cents)


def evaluate(root):
    intake = load(root, "intake/adoption_intake.py")
    foster = load(root, "foster/foster_sync.py")
    returned_test = load(root, "checks/returned_animal_test.py")

    local = regular_case(intake)
    local_result = intake["adopt"](local, "R-9")

    away = regular_case(intake, outside=True)
    remote_a_before = foster["synchronized_state"](away)
    remote_a_result = intake["adopt"](away, "R-10")
    remote_a_after = foster["synchronized_state"](away)

    remote_b_case = returned_case(
        intake,
        "A-8",
        {"reason": "vaccination lapse", "recorded_on": "2026-01-14"},
        "R-8",
        7315,
    )
    history_before = deepcopy(remote_b_case["history"]["hold"])
    payment_before = deepcopy(remote_b_case["adoptions"][0])
    remote_b_result = intake["return_to" + "_shelter"](remote_b_case)

    restored = returned_case(
        intake,
        "A-19",
        {"reason": "bite quarantine", "recorded_on": "2026-02-03"},
        "R-19",
        14800,
    )
    restore_history = deepcopy(restored["history"]["hold"])
    restore_payment = deepcopy(restored["adoptions"][0])
    expected_sync_state = "unavailable"
    first_return = intake["return_to" + "_shelter"](restored)
    state_after_first = foster["synchron" + "ized_state"](restored)
    second_return = intake["return_to" + "_shelter"](restored)
    retry_result = intake["adopt"](restored, "R-11")

    values = (
        ("local-a", local_result is True),
        ("local-b", local["state"] == "adopted"),
        (
            "remote-a",
            remote_a_before == "unavailable"
            and remote_a_result is False
            and remote_a_after == remote_a_before,
        ),
        (
            "remote-b",
            remote_b_result is True
            and returned_test["return_" + "requirements_" + "met"](remote_b_case, history_before, payment_before),
        ),
        (
            "restore",
            first_return is True
            and second_return is True
            and state_after_first == expected_sync_state
            and foster["synchron" + "ized_state"](restored) == expected_sync_state
            and retry_result is False
            and returned_test["return_" + "requirements_" + "met"](restored, restore_history, restore_payment)
            and len(restored["refunds"]) == 1
        ),
    )
    return {role: passed for role, passed in values}


def main():
    values = evaluate(pathlib.Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
