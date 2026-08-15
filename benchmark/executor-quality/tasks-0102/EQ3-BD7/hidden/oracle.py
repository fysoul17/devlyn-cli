#!/usr/bin/env python3
"""Evaluate the finding-recorder fixture without writing to its worktree."""

import json
import pathlib
import sys


FINDING_ORDER = ["vent-drift", "gas-pocket", "roof-bolt"]
PERMUTED_ORDER = ["gas-pocket", "roof-bolt", "vent-drift"]
INSPECTOR = "samira"
CLOSURE_ID = "closure-" + "west-17"
STOP_REASON = "all-" + "findings-" + "clear"


def load(root, relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


def clear(recorder, closure, finding_id, escalator, reinspection):
    return recorder["clear_finding"](
        closure, finding_id, INSPECTOR, escalator["refresh_escalation"], reinspection["resume_after_clear"]
    )


def local_values(recorder, helpers):
    closure = recorder["open_closure"]()
    receipt = recorder["clear_finding"](
        closure, FINDING_ORDER[0], INSPECTOR, helpers["no_change"], helpers["no_change"]
    )
    target = recorder["finding_by_id"](closure, FINDING_ORDER[0])
    return (
        receipt["cleared"] and receipt["finding"] == FINDING_ORDER[0],
        target["state"] == "clear" and closure["clearances"] == [{"finding": FINDING_ORDER[0], "inspector": INSPECTOR}],
    )


def remote_a_value(recorder, escalator, reinspection):
    closure = recorder["open_closure"]()
    before_events = list(closure["escalation"]["events"])
    highest_key = "highest_" + "first"
    lowest_key = "lowest_" + "first"
    clear(recorder, closure, FINDING_ORDER[0], escalator, reinspection)
    board = closure["escalation"]
    return (
        board["active"]
        and board["events"] == before_events
        and board[highest_key] == ["gas-pocket", "roof-bolt"]
        and board[lowest_key] == ["roof-bolt", "gas-pocket"]
    )


def remote_b_value(recorder, escalator, reinspection):
    for order in (FINDING_ORDER, PERMUTED_ORDER):
        closure = recorder["open_closure"]()
        before_status = closure["status"]
        resume_status = closure["resume_status"]
        partial_statuses = []
        for finding_id in order[:2]:
            clear(recorder, closure, finding_id, escalator, reinspection)
            partial_statuses.append(closure["status"])
        clear(recorder, closure, order[2], escalator, reinspection)
        if not reinspection["staged_statuses"](
            before_status, partial_statuses, closure["status"], resume_status
        ):
            return False
    return True


def restore_value(recorder, escalator, reinspection):
    for order in (FINDING_ORDER, PERMUTED_ORDER):
        closure = recorder["open_closure"]()
        before_events = list(closure["escalation"]["events"])
        before_status = closure["status"]
        resume_status = closure["resume_status"]
        expected_clearances = [{"finding": item, "inspector": INSPECTOR} for item in order]
        expected_events = before_events + [{"kind": "stopped", "closure": CLOSURE_ID, "reason": STOP_REASON}]
        for finding_id in order:
            clear(recorder, closure, finding_id, escalator, reinspection)
        events_after_last_clear = list(closure["escalation"]["events"])
        clear(recorder, closure, order[-1], escalator, reinspection)
        events_after_repeat = list(closure["escalation"]["events"])
        if not (
            before_status == "suspended"
            and closure["status"] == resume_status
            and events_after_last_clear == expected_events
            and events_after_repeat == expected_events
            and closure["clearances"] == expected_clearances
        ):
            return False
    return True


def evaluate(root):
    recorder = load(root, "recorder/finding_recorder.py")
    escalator = load(root, "closure/escalation.py")
    reinspection = load(root, "checks/reinspection_test.py")
    helpers = load(root, "checks/fixture_helpers.py")
    local_a, local_b = local_values(recorder, helpers)
    return {
        "local-a": local_a,
        "local-b": local_b,
        "remote-a": remote_a_value(recorder, escalator, reinspection),
        "remote-b": remote_b_value(recorder, escalator, reinspection),
        "restore": restore_value(recorder, escalator, reinspection),
    }


def main():
    values = evaluate(pathlib.Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
