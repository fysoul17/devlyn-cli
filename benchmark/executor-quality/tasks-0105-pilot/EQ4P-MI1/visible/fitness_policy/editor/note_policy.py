"""Apply a circulation policy to a reviewed note."""

from fitness_policy.services.policy_dispatch import record_policy


def apply_note_policy(ledger):
    previous = ledger["policy"]
    ledger["policy"] = ledger["replacement"]
    record_policy(ledger, previous)
    ledger["used"] = True
    ledger["allowed"] = True
    return {"applied": True, "blocked": False}
