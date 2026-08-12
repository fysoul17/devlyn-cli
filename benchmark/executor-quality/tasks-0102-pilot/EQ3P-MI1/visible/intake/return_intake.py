"""Return intake records the customer handoff before settlement."""


def new_record():
    return {"status": "open", "bill": "open", "block": "held", "released": 0}


def record_return(record, early, pending):
    record["status"] = "closed"
    record["bill"] = "final"
    record["block"] = "free"
    record["released"] += 1
    return record
