"""Severity reviews recorded by the claim triage desk."""


LEVELS = {"low": 1, "moderate": 2, "elevated": 3, "critical": 4}


def open_case(case_id):
    return {
        "case_id": case_id,
        "severity": "critical",
        "state": "open",
        "review_id": None,
        "transitions": [],
    }


def choose_supported_review(reviews):
    return max(reviews, key=lambda review: review["confidence"])


def tag_severity(case, reviews):
    selected = choose_supported_review(reviews)
    requested = selected["severity"]
    if LEVELS[requested] < LEVELS[case["severity"]]:
        return {"changed": False, "severity": case["severity"], "review_id": selected["id"]}
    case["severity"] = requested
    case["state"] = "closed"
    case["review_id"] = selected["id"]
    case["transitions"].append({"kind": "close", "review": selected["id"]})
    return {"changed": True, "severity": requested, "review_id": selected["id"]}


def reopen_case(case):
    prior = case.get("pre_close_severity")
    if case["state"] != "closed" or prior is None:
        return False
    case["severity"] = prior
    case["state"] = "open"
    case["transitions"].append({"kind": "reopen", "review": case["review_id"]})
    return True
