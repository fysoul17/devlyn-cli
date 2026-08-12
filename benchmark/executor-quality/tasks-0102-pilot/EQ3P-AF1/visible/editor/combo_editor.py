"""Maintain concession combos during one cinema shift."""


def open_shift():
    return {
        "stock": {"corn": 2, "fizz": 1},
        "component_map": {"matinee": ("corn", "fizz")},
        "reservations": [],
        "reserved": 0,
        "expired": set(),
        "spoilage": 0,
        "refunds": 0,
    }


def reserve_combo(shift):
    return shift


def expire_component(shift, component):
    shift["expired"].add(component)
    shift["spoilage"] += 1
    return shift


def combo_available(shift):
    return shift["stock"]["corn"] > 0 and shift["stock"]["fizz"] > 0
