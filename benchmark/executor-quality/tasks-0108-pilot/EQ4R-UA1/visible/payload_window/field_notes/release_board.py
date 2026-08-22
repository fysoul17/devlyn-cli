"""Summarize payload release items for shift turnover.

The board lists acceptance for a released slot and its replacement.
"""


def release_item(payload, replacement):
    return {"payload": payload, "replacement": replacement, "state": "acceptance"}
