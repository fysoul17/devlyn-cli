"""Write a concise payload status brief for launch coordination.

The brief carries acceptance after a routine hold is reviewed by the crew.
"""


def brief_status(payload, hold):
    return {"payload": payload, "hold": hold, "state": "acceptance"}
