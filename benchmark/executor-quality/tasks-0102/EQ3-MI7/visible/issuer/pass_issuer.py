"""Pass issue and close actions used by the resort counter."""


def issue_pass(pass_id, price, scheduled_windows):
    return {
        "id": pass_id,
        "price": price,
        "scheduled_windows": scheduled_windows,
        "active": True,
        "uses": [],
        "refunds": [],
        "invalidations": [],
    }


def close_pass(pass_record):
    return {"closed": False, "amount": 0, "pass_id": pass_record["id"]}
