"""A compact status check for local development."""


def closed(case):
    return case["state"] == "closed"
