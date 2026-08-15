"""Regression helpers for refill authorization accounting.

A partial fill debit is written once for an accepted identifier. A released
candidate contributes no debit row, leaving the authorization ledger usable.
"""


def partial_fill_debits_once(state, accepted_id, rejected_id):
    accepted = [row for row in state["debits"] if row["fill_id"] == accepted_id]
    rejected = [row for row in state["debits"] if row["fill_id"] == rejected_id]
    return len(accepted) == 1 and not rejected


def released_units_match(state, fill_id, units):
    rows = [row for row in state["release_log"] if row["fill_id"] == fill_id]
    return len(rows) == 1 and rows[0]["units"] == units
