"""Daily counter report helpers."""


def total_amount(records):
    return sum(record["amount"] for record in records)
