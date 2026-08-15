"""List cases currently away from the main shelter."""


def away_case_ids(cases):
    return [case["id"] for case in cases if case["outside"]]
