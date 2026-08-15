"""Evaluate the enrollment fixture without mutating the supplied worktree."""

import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


desk = load("intake/consent_recorder.py")
draws = load("cohorts/cohort_randomizer.py")
release_case = load("checks/withdrawal_release_test.py")


def prepared():
    trial = draws["new_trial"]()
    participant = desk["new_participant"]("participant-7")
    first = desk["record_consent"](participant, "v1", draws["reserve"], trial)
    first_slot = participant["slot"]
    left_once = desk["withdraw"](participant, draws["release"], trial)
    left_twice = desk["withdraw"](participant, draws["release"], trial)
    return trial, participant, first, first_slot, left_once, left_twice


local_trial, local_person, local_first, local_slot, _, _ = prepared()
local_second = desk["record_consent"](local_person, "v2", draws["reserve"], local_trial)

remote_trial, remote_person, _, remote_slot, _, _ = prepared()
remote_second = desk["record_consent"](remote_person, "v2", draws["reserve"], remote_trial)

restore_trial, restore_person, restore_first, restore_slot, restore_left, restore_repeat = prepared()
restore_second = desk["record_consent"](restore_person, "v2", draws["reserve"], restore_trial)

values = [
    ("local-a", local_first["accepted"] and local_second["accepted"]),
    ("local-b", local_person["current" + "_form"] == "v2" and local_person["active"]),
    ("remote-a", remote_second["accepted"] and draws["uses_baseline"](remote_trial, remote_person["id"], "v1")),
    ("remote-b", release_case["slot_vacated"](remote_trial, remote_slot)),
    ("restore", restore_first["accepted"] and restore_left and not restore_repeat
     and restore_second["accepted"] and restore_person["slot"] != restore_slot
     and restore_trial["vacated"] == [restore_slot]
     and [row["slot"] for row in restore_trial["requests"]] == [restore_slot, restore_person["slot"]]
     and draws["uses_baseline"](restore_trial, restore_person["id"], "v1")),
]
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
