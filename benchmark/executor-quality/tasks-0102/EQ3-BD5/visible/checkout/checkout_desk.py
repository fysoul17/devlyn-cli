"""Checkout-desk actions used by the stage manager."""


def open_show():
    return {
        "ledger": [
            {"id": "r-11", "scene": "act-2", "prop": "clock-main"},
            {"id": "r-12", "scene": "act-2", "prop": "book-red"},
            {"id": "r-13", "scene": "act-3", "prop": "clock-main"},
        ],
        "understudies": {"clock-main": "clock-understudy"},
        "damage_log": [],
    }


def report_damage(show, prop, scene):
    return {"swapped": False, "replacement": None, "scene": scene}


def checked_out_props(show, scene):
    return [entry["prop"] for entry in show["ledger"] if entry["scene"] == scene]
