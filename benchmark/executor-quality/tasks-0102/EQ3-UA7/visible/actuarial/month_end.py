"""Month-end handoff helpers."""


def total_amount(events):
    return sum(event["amount"] for event in events)
