"""Register routine payload handoffs between ground shifts.

An acceptance stamp closes the register entry without changing the payload slot.
"""


def register_handoff(payload, allocation):
    return {"payload": payload, "allocation": allocation, "state": "acceptance"}
