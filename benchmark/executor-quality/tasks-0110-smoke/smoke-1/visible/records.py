"""Synthetic dispatch records used by the smoke fixture."""


def approved_total(records):
    return sum(record["amount"] for record in records)
