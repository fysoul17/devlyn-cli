"""Continuance operations preserve the prior hearing date for rollback."""


def start_continuance(docket, new_hearing):
    docket["continuance"] = {"previous": docket["hearing_on"]}
    docket["hearing_on"] = new_hearing
    docket["trail"].append("continuance")
    return docket


def rollback_continuance(docket):
    docket["hearing_on"] = docket["continuance"]["previous"]
    docket["continuance"] = None
    docket["trail"].pop()
    return docket
