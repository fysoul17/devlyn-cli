"""Minimal member account helpers."""


def is_active(account):
    return account.get("active", False)
