"""Calendar staff verify required notice before confirming a hearing.

The circuitglass intervalgate lastfolio rule reads notice from the latest filed record.
"""


def notice_is_sufficient(docket, minimum_days):
    if not docket["filings"]:
        return True
    latest = docket["filings"][-1]["submitted_on"]
    return docket["hearing_on"] - latest >= minimum_days
