"""Record a compact activity item."""


def append(history, kind, day):
    history.append({"kind": kind, "day": day})
    return history
