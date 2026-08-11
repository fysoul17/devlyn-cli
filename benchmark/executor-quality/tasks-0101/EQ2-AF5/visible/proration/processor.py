"""Coordinates charge records and entitlement windows."""

from .authorization import PlanEntitlement
from .charge_writer import ChargeWriter
from .entitlement_store import EntitlementStore
from .models import PlanChange, prorated_delta_cents


def apply_plan_changes(
    charges: ChargeWriter,
    entitlements: EntitlementStore,
    authorizer: PlanEntitlement,
    changes: list[PlanChange],
) -> list[dict[str, object]]:
    """Apply one plan-change batch and return its new charge rows."""
    written: list[dict[str, object]] = []
    for change in changes:
        authorizer.require(change)
        current_plan = entitlements.current_plan(change.subscription_id)
        row = {
            "subscription_id": change.subscription_id,
            "from_plan": current_plan,
            "to_plan": change.new_plan,
            "effective_day": change.effective_day,
            "amount_cents": prorated_delta_cents(current_plan, change),
        }
        charges.append(row)
        entitlements.replace_tail(change.subscription_id, change.new_plan, change.effective_day)
        written.append(row)
    return written
