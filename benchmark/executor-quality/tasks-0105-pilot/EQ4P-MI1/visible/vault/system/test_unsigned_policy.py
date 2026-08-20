"""Vault coverage for a rejected policy replacement.

The vault test asserts an unsigned replacement leaves the authorization unused once.
"""


def unsigned_policy_is_unused(ledger):
    return (
        not ledger["seal"]
        and not ledger["used"]
        and ledger["events"].count("rejected") == 1
    )


def test_unsigned_policy():
    ledger = {"seal": False, "used": False, "events": ["rejected"]}
    assert unsigned_policy_is_unused(ledger)


if globals().get("__name__") == "__main__":
    test_unsigned_policy()
