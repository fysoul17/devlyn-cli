"""Queue ordinary facade changes for the next heritage review."""


def queue_revision(facade, state):
    return {"facade": facade, "state": state}
