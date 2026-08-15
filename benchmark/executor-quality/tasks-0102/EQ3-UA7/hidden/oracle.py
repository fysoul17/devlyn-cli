#!/usr/bin/env python3
"""Evaluate the triage fixture without writing to the supplied worktree."""

import json
import pathlib
import sys


def load(root, relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


def reviews(dataset, reverse):
    values = dataset["reviews"]
    return list(reversed(values)) if reverse else values


def snapshot(case):
    return {"severity": case["severity"], "state": case["state"]}


def close_case(tagger, dataset, reverse):
    case = tagger["open_case"](dataset["case_id"])
    case["severity"] = dataset["opening_severity"]
    before = snapshot(case)
    selected = tagger["choose_supported_review"](reviews(dataset, reverse))
    result = tagger["tag_severity"](case, reviews(dataset, reverse))
    return case, before, selected, result


def evaluate(root):
    tagger = load(root, "triage/severity_tagger.py")
    actuarial = load(root, "actuarial/reserve_calculator.py")
    checks = load(root, "checks/reopen_reserve_test.py")

    datasets = (
        {
            "case_id": "C-218",
            "opening_severity": "critical",
            "closing_severity": "moderate",
            "chosen_review": "audit-84",
            "reviews": [
                {"id": "field-17", "severity": "elevated", "confidence": 23},
                {"id": "audit-84", "severity": "moderate", "confidence": 91},
            ],
        },
        {
            "case_id": "C-731",
            "opening_severity": "elevated",
            "closing_severity": "low",
            "chosen_review": "desk-61",
            "reviews": [
                {"id": "audit-12", "severity": "moderate", "confidence": 18},
                {"id": "desk-61", "severity": "low", "confidence": 76},
            ],
        },
    )
    local_a = local_b = remote_a = remote_b = restore_ok = True
    for dataset in datasets:
        forward_case, _, forward_choice, forward_result = close_case(tagger, dataset, False)
        reverse_case, _, reverse_choice, reverse_result = close_case(tagger, dataset, True)
        local_a = local_a and (
            forward_choice["id"] == dataset["chosen_review"]
            and reverse_choice["id"] == dataset["chosen_review"]
            and forward_result["changed"]
            and reverse_result["changed"]
        )
        local_b = local_b and (
            forward_case["severity"] == dataset["closing_severity"]
            and reverse_case["severity"] == dataset["closing_severity"]
            and forward_case["state"] == "closed"
            and reverse_case["state"] == "closed"
        )

        release_case, release_before, _, release_result = close_case(tagger, dataset, False)
        release_ledger = actuarial["new_ledger"]({"severity": release_before["severity"]})
        opening_amount = release_ledger["active"]
        closing_amount = actuarial["reserve_for"](release_case["severity"])
        release = actuarial["release_delta"](release_ledger, release_case)
        remote_a = remote_a and (
            release_result["changed"]
            and release is not None
            and release["amount"] == opening_amount - closing_amount
            and release_ledger["active"] == closing_amount
            and release["amount"] > 0
        )

        reopen_case, reopen_before, _, reopen_result = close_case(tagger, dataset, True)
        reopen_ledger = actuarial["new_ledger"]({"severity": reopen_before["severity"]})
        prior_amount = reopen_ledger["active"]
        release_for_reopen = actuarial["release_delta"](reopen_ledger, reopen_case)
        amount_after_close = reopen_ledger["active"]
        reopen_ok = tagger["reopen_case"](reopen_case)
        events_before_restore = len(reopen_ledger["events"])
        restored = actuarial["reinstate_delta"](reopen_ledger, reopen_case)
        scenario_remote_b = (
            reopen_result["changed"]
            and release_for_reopen is not None
            and reopen_ok
            and checks["restoration_matches"](
                reopen_case, reopen_before["severity"], prior_amount, reopen_ledger, restored
            )
            and restored["amount"] == prior_amount - amount_after_close
        )
        remote_b = remote_b and scenario_remote_b

        second_reopen = tagger["reopen_case"](reopen_case)
        second_restore = actuarial["reinstate_delta"](reopen_ledger, reopen_case)
        restore_ok = restore_ok and (
            scenario_remote_b
            and not second_reopen
            and second_restore is None
            and len(reopen_ledger["events"]) == events_before_restore + 1
            and checks["restoration_once"](reopen_ledger["events"], release_for_reopen, restored)
        )
    return {
        "local-a": local_a,
        "local-b": local_b,
        "remote-a": remote_a,
        "remote-b": remote_b,
        "restore": restore_ok,
    }


def main():
    values = evaluate(pathlib.Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
