"""Daily desk report helpers."""


def state_counts(cases):
    return {state: sum(case["state"] == state for case in cases) for state in {case["state"] for case in cases}}
