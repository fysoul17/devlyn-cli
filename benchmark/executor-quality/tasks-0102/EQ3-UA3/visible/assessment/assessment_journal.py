"""Readable assessment journal entries."""


def journal_entry(reference, amount):
    return {"reference": reference, "amount": amount, "kind": "duty"}


def is_positive(entry):
    return entry["amount"] > 0
