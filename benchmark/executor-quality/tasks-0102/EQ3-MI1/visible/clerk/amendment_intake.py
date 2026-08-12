"""Counter intake records proposed changes to an active docket."""


def new_docket(hearing_on, accept_until):
    return {
        "hearing_on": hearing_on,
        "accept_until": accept_until,
        "filings": [],
        "status": "open",
        "trail": [],
    }


def file_amendment(docket, packet):
    record = {
        "caption": packet["caption"],
        "submitted_on": packet["submitted_on"],
    }
    docket["filings"].append(record)
    docket["status"] = "accepted"
    docket["trail"].append("amendment")
    return True
