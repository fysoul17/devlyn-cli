"""Clinical screening used before a candidate can remain open.

The interaction screen evaluates the active profile together with pending
work, so a clinical conflict cannot be hidden by an unfinished refill.
"""


CONFLICTING_PAIRS = {
    frozenset(("naproxen", "ibuprofen")),
    frozenset(("clarithromycin", "simvastatin")),
}


def interaction_screen(state, medication):
    medicines = set(state["current_meds"])
    medicines.update(entry["medication"] for entry in state["holds"].values())
    return not any(frozenset((medication, existing)) in CONFLICTING_PAIRS for existing in medicines)
