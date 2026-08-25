"""Synthetic handoff queue used by the smoke fixture."""


def ordered_open_cases(cases):
    open_cases = [case for case in cases if case["status"] == "open"]
    return sorted(open_cases, key=lambda case: case["deadline"], reverse=True)
