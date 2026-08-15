"""Historical review display."""


def transition_kinds(case):
    return [item["kind"] for item in case["transitions"]]
