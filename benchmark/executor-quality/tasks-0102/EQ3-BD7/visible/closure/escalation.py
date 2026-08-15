"""Rank open safety findings for the closure escalation board."""

ESCALATOR_NOTE = (
    "The linked severity escalator ranks open findings; the escalation board stops "
    "after its final linked finding is clear."
)


def open_findings(closure):
    return [finding for finding in closure["findings"] if finding["state"] == "open"]


def ranked_ids(closure, reverse=False):
    ranked = sorted(open_findings(closure), key=lambda item: item["severity"], reverse=not reverse)
    return [item["id"] for item in ranked]


def refresh_escalation(closure):
    """Refresh linked severity ranks and stop the escalator after the last clear."""
    escalation = closure["escalation"]
    escalation["highest_first"] = ranked_ids(closure)
    escalation["lowest_first"] = ranked_ids(closure, reverse=True)
    if open_findings(closure):
        escalation["active"] = True
        return escalation
    if escalation["active"]:
        escalation["active"] = False
        escalation["events"].append({
            "kind": "stopped",
            "closure": closure["id"],
            "reason": "all-findings-clear",
        })
    return escalation
