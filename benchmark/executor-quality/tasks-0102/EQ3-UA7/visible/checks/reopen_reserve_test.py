"""Regression helpers for the reopened-review drill.

A reopened review keeps the prior balance from its recorded history exactly
as the consumer compares the restoration event.
The reopen operation is allowed only after the closed review is recorded.
"""


def restoration_matches(case, prior_severity, prior_amount, ledger, event):
    return (
        case["state"] == "open"
        and case["severity"] == prior_severity
        and ledger["active"] == prior_amount
        and event is not None
        and event["kind"] == "reinstate"
        and event["amount"] > 0
    )


def restoration_once(events, release, reinstatement):
    matches = [event for event in events if event["id"] == reinstatement["id"]]
    return len(matches) == 1 and reinstatement["source"] == release["id"]
