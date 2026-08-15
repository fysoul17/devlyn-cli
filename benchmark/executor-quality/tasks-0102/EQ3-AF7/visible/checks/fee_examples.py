"""Examples used by staff when reviewing ordinary receipt amounts."""


def total_fees(payments):
    return sum(item["fee_cents"] for item in payments)
