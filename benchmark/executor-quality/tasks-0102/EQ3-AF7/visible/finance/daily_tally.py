"""Build a compact total for a group of cases."""


def daily_total(cases):
    return sum(
        sum(item["fee_cents"] for item in case["adoptions"])
        - sum(item["fee_cents"] for item in case["refunds"])
        for case in cases
    )
