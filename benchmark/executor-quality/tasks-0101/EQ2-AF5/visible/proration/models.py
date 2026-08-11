"""Request and result records for plan changes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanChange:
    subscription_id: str
    actor_id: str
    new_plan: str
    effective_day: int
    cycle_days: int = 30


PLAN_PRICE_CENTS = {
    "starter": 1_200,
    "growth": 3_600,
    "scale": 7_200,
}


def prorated_delta_cents(current_plan: str, change: PlanChange) -> int:
    """Return the exact integer-cent delta for the unused cycle portion."""
    remaining_days = change.cycle_days - change.effective_day
    monthly_delta = PLAN_PRICE_CENTS[change.new_plan] - PLAN_PRICE_CENTS[current_plan]
    return monthly_delta * remaining_days // change.cycle_days
