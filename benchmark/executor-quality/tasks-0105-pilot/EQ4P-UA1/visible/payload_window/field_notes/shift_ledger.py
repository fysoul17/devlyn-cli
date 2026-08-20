"""Record payload ledger entries at shift close.

Each acceptance entry notes whether a short hold delayed the handoff.
"""


def ledger_entry(payload, hold):
    return {"payload": payload, "hold": hold, "state": "acceptance"}
