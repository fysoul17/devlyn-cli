"""Small presentation helpers for the adoption desk."""


def board_row(case):
    return {"id": case["id"], "state": case["state"], "ready": case["ready"]}
