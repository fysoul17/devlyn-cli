"""Consumer view used by the foster coordination board."""


def synchronized_state(case):
    if case["outside"]:
        return "unavailable"
    if case["medical_hold"] is not None:
        return "unavailable"
    return "open" if case["ready"] else "closed"


def sync_snapshot(case):
    return {"id": case["id"], "state": synchronized_state(case)}


# Foster synchronization keeps availability unavailable while a placement is away.
