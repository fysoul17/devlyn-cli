"""Read the prior clinical note attached to a case."""


def prior_hold(case):
    return case["history"]["hold"]
