"""Record individual mine findings during a field review."""


def open_closure():
    findings = [
        {"id": "vent-drift", "severity": 2, "state": "open"},
        {"id": "gas-pocket", "severity": 7, "state": "open"},
        {"id": "roof-bolt", "severity": 5, "state": "open"},
    ]
    return {
        "id": "closure-west-17",
        "status": "suspended",
        "resume_status": "operating",
        "findings": findings,
        "clearances": [],
        "escalation": {
            "active": True,
            "events": [{"kind": "raised", "closure": "closure-west-17", "finding": "gas-pocket"}],
            "highest_first": ["gas-pocket", "roof-bolt", "vent-drift"],
            "lowest_first": ["vent-drift", "roof-bolt", "gas-pocket"],
        },
    }


def finding_by_id(closure, finding_id):
    for finding in closure["findings"]:
        if finding["id"] == finding_id:
            return finding
    raise KeyError(finding_id)


def clear_finding(closure, finding_id, inspector, update_escalation, resume_status):
    """Record one verified finding and return its desk receipt."""
    return {"finding": finding_id, "cleared": False, "inspector": inspector}
