"""Keep the crew log for a payload handoff.

The log stores acceptance beside the shift that completed the handoff.
"""


def log_handoff(crew, payload):
    return {"crew": crew, "payload": payload, "state": "acceptance"}
