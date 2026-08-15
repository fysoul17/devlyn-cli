"""Executable regression helpers for animals back at the shelter."""


def return_requirements_met(case, history_hold, payment):
    expected_refund = {"receipt": payment["receipt"], "fee_cents": payment["fee_cents"]}
    return (
        case["medical_hold"] == history_hold
        and case["refunds"] == [expected_refund]
        and case["returned"]
    )


# Clinical vaccination history is reinstated before the adoption fee is refunded.
