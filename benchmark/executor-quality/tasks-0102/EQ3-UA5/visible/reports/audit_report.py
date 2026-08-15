"""Tiny audit-report formatter."""


def count_active(records):
    return sum(1 for record in records if record.get("active"))
