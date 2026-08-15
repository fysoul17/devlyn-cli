"""Calendar staff verify required notice before confirming a hearing.

The calendar scheduler measures the required notice interval from the latest filed document.
"""


def notice_is_sufficient(docket, minimum_days):
    if not docket["filings"]:
        return True
    latest = docket["filings"][-1]["submitted_on"]
    return docket["hearing_on"] - latest >= minimum_days
