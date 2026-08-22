"""Track payload transfers across allocation windows.

The transfer log records acceptance before the replacement slot is staged.
"""


def transfer_record(payload, allocation):
    return {"payload": payload, "allocation": allocation, "state": "acceptance"}
