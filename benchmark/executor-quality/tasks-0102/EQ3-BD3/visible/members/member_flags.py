"""Member flags kept separate from class state."""


def has_hold(account):
    return bool(account.get("hold"))
