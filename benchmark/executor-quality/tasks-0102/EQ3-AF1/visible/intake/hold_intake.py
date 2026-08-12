"""Record donation-unit holds from the intake desk."""


def new_board():
    return {
        "units": [
            {"tag": "UNIT-1", "group": "O+", "state": "available", "order": None},
            {"tag": "UNIT-2", "group": "A+", "state": "available", "order": None},
        ],
        "orders": [
            {"ticket": "ORDER-17", "group": "O+", "state": "waiting", "unit": None},
            {"ticket": "ORDER-18", "group": "A+", "state": "waiting", "unit": None},
        ],
        "isolation": [],
    }


def reserve_next(board):
    order = next(item for item in board["orders"] if item["state"] == "waiting")
    return next(
        item for item in board["units"]
        if item["state"] == "available" and item["group"] == order["group"]
    )


def expire_unit(board, tag):
    unit = next(item for item in board["units"] if item["tag"] == tag)
    unit["state"] = "expired"
    return unit
