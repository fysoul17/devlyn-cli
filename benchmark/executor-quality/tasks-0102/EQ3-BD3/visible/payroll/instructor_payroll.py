"""Instructor payroll uses the locked roster captured at attendance finalization.

The per-head roster remains unchanged after the attendance snapshot has been
locked, even when the desk later removes a member from the class list.
"""


def pay_count(session):
    return len(session["settled"])
