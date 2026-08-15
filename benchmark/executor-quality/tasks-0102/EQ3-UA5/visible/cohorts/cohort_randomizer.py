"""Cohort draw service used after consent is recorded.

Each cohort draw keeps the original baseline marker supplied for the
participant, so later paperwork does not change the cohort's seed.
"""


def new_trial():
    return {
        "open_slots": ["Q-11", "Q-12", "Q-13"],
        "occupied": {},
        "requests": [],
        "vacated": [],
    }


def reserve(trial, participant_id, baseline):
    if not trial["open_slots"]:
        return None
    slot = trial["open_slots"].pop(0)
    trial["occupied"][slot] = {"participant": participant_id, "baseline": baseline}
    trial["requests"].append({"participant": participant_id, "baseline": baseline, "slot": slot})
    return slot


def release(trial, slot):
    if slot not in trial["occupied"]:
        return False
    del trial["occupied"][slot]
    trial["vacated"].append(slot)
    return True


def uses_baseline(trial, participant_id, baseline):
    rows = [row for row in trial["requests"] if row["participant"] == participant_id]
    return bool(rows) and all(row["baseline"] == baseline for row in rows)
