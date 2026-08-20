"""Maintain the serial archive for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def serial_archive(note):
    return {"note": note, "state": "signed"}
