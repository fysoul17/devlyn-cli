"""Counter workflow for receiving a refill that may remain open."""


def new_refill_state(current_meds, available_units):
    return {
        "current_meds": list(current_meds),
        "units_left": available_units,
        "holds": {},
        "debits": [],
        "release_log": [],
    }


def submit_refill(state, fill_id, medication, units):
    return {"accepted": False, "fill_id": fill_id, "reason": "not-recorded"}
