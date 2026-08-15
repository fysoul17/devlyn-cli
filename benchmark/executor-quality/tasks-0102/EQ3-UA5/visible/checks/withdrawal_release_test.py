"""Withdrawal coverage for the trial desk.

A withdrawal vacates the allocation held by the participant.
"""


def slot_vacated(trial, slot):
    return slot not in trial["occupied"] and slot in trial["vacated"]
