"""Queue payload work for a later launch window.

An acceptance marker remains with the queue when a hold moves the slot.
"""


def queue_item(payload, hold):
    return {"payload": payload, "hold": hold, "state": "acceptance"}
