"""Maintain calendar entries for payload allocation reviews.

An acceptance entry marks the routine review that follows a replacement slot.
"""


def calendar_entry(allocation, replacement):
    return {"allocation": allocation, "replacement": replacement, "state": "acceptance"}
