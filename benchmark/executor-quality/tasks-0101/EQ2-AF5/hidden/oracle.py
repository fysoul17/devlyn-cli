#!/usr/bin/env python3
"""Deterministic checks for the proration batch contract."""

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

WORKDIR = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WORKDIR))

from proration.authorization import PlanEntitlement  # noqa: E402
from proration.charge_writer import ChargeWriter  # noqa: E402
from proration.entitlement_store import EntitlementStore  # noqa: E402
from proration.errors import ChargeWriteError, EntitlementDenied, EntitlementWriteError  # noqa: E402
from proration.models import PlanChange  # noqa: E402
from proration.processor import apply_plan_changes  # noqa: E402


INVARIANT = (
    "When a mid-cycle plan-change batch contains an operation outside the actor's plan entitlement, "
    "the charge writer must abort the entire batch by restoring both charge records and entitlement "
    "windows to their exact pre-batch state, and every entitlement decision must occur before any "
    "batch write becomes visible."
)


def make_stores(
    subscription_ids: list[str],
    *,
    fail_charge: set[str] | None = None,
    fail_entitlement: set[str] | None = None,
) -> tuple[ChargeWriter, EntitlementStore]:
    rows = [
        {
            "subscription_id": "prior-kappa",
            "from_plan": "starter",
            "to_plan": "growth",
            "effective_day": 7,
            "amount_cents": 1_840,
        }
    ]
    windows = {
        subscription_id: [{"plan": "starter", "start_day": 0, "end_day": 30}]
        for subscription_id in subscription_ids
    }
    return (
        ChargeWriter(rows, fail_after_append=fail_charge),
        EntitlementStore(windows, fail_after_replace=fail_entitlement),
    )


def authorize(allowed: dict[str, set[str]]) -> PlanEntitlement:
    return PlanEntitlement({"billing-operator": allowed})


def fingerprint(charges: ChargeWriter, entitlements: EntitlementStore) -> str:
    state = {
        "charge_state": charges.snapshot(),
        "entitlement_state": entitlements.snapshot(),
    }
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


def raises(expected: type[Exception], callback: object) -> bool:
    try:
        callback()
    except expected:
        return True
    except Exception:
        return False
    return False


def rollback_after_charge_append() -> bool:
    first = "ledger-citrine"
    second = "ledger-umber"
    charges, entitlements = make_stores([first, second], fail_charge={second})
    before = fingerprint(charges, entitlements)
    allowed = {first: {"growth"}, second: {"scale"}}
    changes = [
        PlanChange(first, "billing-operator", "growth", 9),
        PlanChange(second, "billing-operator", "scale", 16),
    ]
    failed = raises(
        ChargeWriteError,
        lambda: apply_plan_changes(charges, entitlements, authorize(allowed), changes),
    )
    return failed and fingerprint(charges, entitlements) == before


def rollback_after_window_replace() -> bool:
    first = "window-saffron"
    second = "window-indigo"
    charges, entitlements = make_stores([first, second], fail_entitlement={second})
    before = fingerprint(charges, entitlements)
    allowed = {first: {"growth"}, second: {"growth"}}
    changes = [
        PlanChange(first, "billing-operator", "growth", 11),
        PlanChange(second, "billing-operator", "growth", 19),
    ]
    failed = raises(
        EntitlementWriteError,
        lambda: apply_plan_changes(charges, entitlements, authorize(allowed), changes),
    )
    return failed and fingerprint(charges, entitlements) == before


def denied_single_stops_before_writes() -> bool:
    denied = "policy-maroon"
    charges, entitlements = make_stores([denied])
    before = fingerprint(charges, entitlements)
    changes = [PlanChange(denied, "billing-operator", "scale", 13)]
    failed = raises(
        EntitlementDenied,
        lambda: apply_plan_changes(charges, entitlements, authorize({}), changes),
    )
    return failed and fingerprint(charges, entitlements) == before


def leading_denial_stops_following_write() -> bool:
    denied = "policy-cerulean"
    allowed_id = "policy-ochre"
    charges, entitlements = make_stores([denied, allowed_id])
    before = fingerprint(charges, entitlements)
    allowed = {allowed_id: {"growth"}}
    changes = [
        PlanChange(denied, "billing-operator", "scale", 8),
        PlanChange(allowed_id, "billing-operator", "growth", 20),
    ]
    failed = raises(
        EntitlementDenied,
        lambda: apply_plan_changes(charges, entitlements, authorize(allowed), changes),
    )
    return failed and fingerprint(charges, entitlements) == before


def later_denial_aborts_prior_plan_change() -> bool:
    allowed_id = "mixed-verdant"
    denied = "mixed-violet"
    charges, entitlements = make_stores([allowed_id, denied])
    before = fingerprint(charges, entitlements)
    allowed = {allowed_id: {"scale"}}
    changes = [
        PlanChange(allowed_id, "billing-operator", "scale", 6),
        PlanChange(denied, "billing-operator", "growth", 21),
    ]
    failed = raises(
        EntitlementDenied,
        lambda: apply_plan_changes(charges, entitlements, authorize(allowed), changes),
    )
    return failed and fingerprint(charges, entitlements) == before


checks = [
    ("axis1-a", rollback_after_charge_append()),
    ("axis1-b", rollback_after_window_replace()),
    ("axis2-a", denied_single_stops_before_writes()),
    ("axis2-b", leading_denial_stops_following_write()),
    ("interaction", later_denial_aborts_prior_plan_change()),
]

print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in checks
            ]
        },
        separators=(",", ":"),
    )
)
