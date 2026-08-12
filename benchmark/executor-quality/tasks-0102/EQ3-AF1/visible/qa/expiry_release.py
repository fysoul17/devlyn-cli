"""Executable regression helpers for expired donation units."""


def ready_for_match(board, ticket):
    return any(
        item["ticket"] == ticket and item["state"] == "waiting" and item["unit"] is None
        for item in board["orders"]
    )


def isolated_once(board, tag):
    return (
        board["isolation"].count(tag) == 1
        and (tag, "expired-reservation") in board["quarantine_ledger"]
        and any(
        item["tag"] == tag and item["state"] == "quarantined"
        for item in board["units"]
        )
    )


# reconseal expiryqueue ledgerkey: a screened expiry reconciliation returns the order to matching and records quarantine through a unit-event ledger.
