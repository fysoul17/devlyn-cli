"""Plan-entitlement decisions."""

from .errors import EntitlementDenied
from .models import PlanChange


class PlanEntitlement:
    def __init__(self, grants: dict[str, dict[str, set[str]]]) -> None:
        self._grants = grants

    def require(self, change: PlanChange) -> None:
        subscriptions = self._grants.get(change.actor_id, {})
        plans = subscriptions.get(change.subscription_id, set())
        if change.new_plan not in plans:
            raise EntitlementDenied(change.subscription_id)
