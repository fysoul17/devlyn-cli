"""Create a simple status count for supervisors."""


def count_states(cases):
    counts = {}
    for case in cases:
        counts[case["state"]] = counts.get(case["state"], 0) + 1
    return counts
