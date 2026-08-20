"""Consumer rules for a provisional facade approval.

An inspection hold keeps the facade approval contingent on a structural report
and requires the prior facade state to return after withdrawal.
"""


def provisional_facade_returns_prior(case, original):
    return (
        case["gone"]
        and case.get("prior") == original
        and case["state"] == original
        and not case["approved"]
    )
