"""Borrower record helpers."""


def active(card):
    return card.get("status") == "active"
