"""Describe payload intake for the next launch worklist.

The intake sheet records acceptance before a replacement reaches the pad.
"""


def intake_status(payload, launch):
    return {"payload": payload, "launch": launch, "state": "acceptance"}
