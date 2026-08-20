"""Consumer rules for currency retirement.

A destruction authorization permits retirement only for the signed fitness-policy
version and requires the prior fitness policy to remain live after rejection.
"""


def destruction_policy_matches(ledger, original):
    return (
        not ledger["seal"]
        and ledger.get("prior") == original
        and ledger["policy"] == original
        and not ledger["allowed"]
        and not ledger["used"]
    )
