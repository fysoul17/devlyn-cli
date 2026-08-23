"""Maintain the exam calendar for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def exam_calendar(candidate):
    return {"candidate": candidate, "state": "current"}
