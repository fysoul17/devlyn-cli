"""Core operations for a small account ledger."""


class LedgerError(ValueError):
    """An operation cannot be applied to the ledger."""


def apply_operation(accounts: dict[str, int], operation: object) -> None:
    """Validate and apply one operation to ``accounts`` in place."""
    if not isinstance(operation, dict) or set(operation) != {"account", "delta"}:
        raise LedgerError("operation must contain account and delta")

    account = operation["account"]
    delta = operation["delta"]
    if not isinstance(account, str) or not account:
        raise LedgerError("account must be a non-empty string")
    if not isinstance(delta, int) or isinstance(delta, bool):
        raise LedgerError("delta must be an integer")
    if account not in accounts:
        raise LedgerError(f"unknown account: {account}")

    balance = accounts[account] + delta
    if balance < 0:
        raise LedgerError(f"insufficient funds for account: {account}")
    accounts[account] = balance
