"""Actuarial reserve calculator for a closed triage review.

The actuarial reserve calculator releases the approved delta only when the
pre-close severity is available to the consumer.
"""


AMOUNTS = {"low": 280, "moderate": 635, "elevated": 875, "critical": 1190}


def reserve_for(severity):
    return AMOUNTS[severity]


def new_ledger(case):
    return {"active": reserve_for(case["severity"]), "events": []}


def release_delta(ledger, case):
    prior = case.get("pre_close_severity")
    if case["state"] != "closed" or prior is None:
        return None
    before, after = reserve_for(prior), reserve_for(case["severity"])
    if ledger["active"] != before or after >= before:
        return None
    event = {
        "id": f"release:{case['review_id']}",
        "kind": "release",
        "amount": before - after,
        "review": case["review_id"],
    }
    if any(item["id"] == event["id"] for item in ledger["events"]):
        return None
    ledger["events"].append(event)
    ledger["active"] = after
    return event


def reinstate_delta(ledger, case):
    releases = [item for item in ledger["events"] if item["kind"] == "release"]
    if case["state"] != "open" or not releases:
        return None
    release = releases[-1]
    after = reserve_for(case["severity"])
    if after <= ledger["active"]:
        return None
    event = {
        "id": f"reinstate:{release['id']}",
        "kind": "reinstate",
        "amount": after - ledger["active"],
        "source": release["id"],
    }
    if any(item["id"] == event["id"] for item in ledger["events"]):
        return None
    ledger["events"].append(event)
    ledger["active"] = after
    return event
