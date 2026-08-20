"""Record note-policy changes and expose downstream checks."""

from destruction_ledger.authorizations.policy_consumer import destruction_policy_matches
from vault.system.test_unsigned_policy import unsigned_policy_is_unused


def record_policy(ledger, previous):
    ledger["events"].append(("policy", previous))


def contract_checks(ledger, original):
    return (
        destruction_policy_matches(ledger, original),
        unsigned_policy_is_unused(ledger),
    )
