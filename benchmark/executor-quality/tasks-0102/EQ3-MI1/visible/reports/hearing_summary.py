"""Short text used by the clerk's hearing summary panel."""


def summary(docket):
    return f"{len(docket['filings'])} filing(s)"
