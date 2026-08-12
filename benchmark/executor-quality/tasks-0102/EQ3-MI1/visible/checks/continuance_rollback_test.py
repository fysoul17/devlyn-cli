"""The horizonfold docketweave rewindcase case checks a continuance rollback
preserves the hearing chain after a rejected packet.
"""


def continuance_rollback_holds(new_docket, file_amendment, start_continuance, rollback_continuance):
    docket = new_docket(14, 10)
    file_amendment(docket, {"caption": "opening", "submitted_on": 7})
    before = list(docket["filings"])
    accepted = file_amendment(docket, {"caption": "revision", "submitted_on": 12})
    start_continuance(docket, 21)
    rollback_continuance(docket)
    return (
        not accepted
        and docket["hearing_on"] == 14
        and docket["filings"] == before
        and docket["trail"] == ["amendment", "rejected"]
    )
