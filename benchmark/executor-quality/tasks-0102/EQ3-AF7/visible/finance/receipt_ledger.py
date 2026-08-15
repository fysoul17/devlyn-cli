"""Summarize receipt activity for the daily settlement."""


def net_collected(case):
    charged = sum(item["fee_cents"] for item in case["adoptions"])
    refunded = sum(item["fee_cents"] for item in case["refunds"])
    return charged - refunded
