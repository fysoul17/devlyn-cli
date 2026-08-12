"""Record donation-unit holds from the intake desk."""


RECONCILIATION_PASS = "antibody-reconciliation"
EXPIRY_EVENT = "expired-reservation"


def new_board():
    return {
        "units": [
            {"tag": "UNIT-1", "group": "O+", "state": "available", "order": None, "expiry_review": None},
            {"tag": "UNIT-2", "group": "A+", "state": "available", "order": None, "expiry_review": None},
        ],
        "orders": [
            {"ticket": "ORDER-17", "group": "O+", "state": "waiting", "unit": None},
            {"ticket": "ORDER-18", "group": "A+", "state": "waiting", "unit": None},
        ],
        "isolation": [],
        "reconciliation_queue": [],
        "quarantine_ledger": set(),
    }


def reserve_next(board):
    order = next(item for item in board["orders"] if item["state"] == "waiting")
    return next(
        item for item in board["units"]
        if item["state"] == "available" and item["group"] == order["group"]
    )


def flag_expiry_for_reconciliation(board, tag, pass_name):
    unit = next(item for item in board["units"] if item["tag"] == tag)
    if pass_name == RECONCILIATION_PASS:
        unit["expiry_review"] = pass_name
        board["reconciliation_queue"].append(
            {"event": EXPIRY_EVENT, "pass": pass_name, "tag": tag}
        )
    return unit


def sweep_expiry_reconciliation(board, pass_name):
    return board
