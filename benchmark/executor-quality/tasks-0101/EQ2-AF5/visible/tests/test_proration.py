"""Public examples for the proration coordinator."""

import unittest

from proration.authorization import PlanEntitlement
from proration.charge_writer import ChargeWriter
from proration.entitlement_store import EntitlementStore
from proration.errors import EntitlementDenied
from proration.models import PlanChange
from proration.processor import apply_plan_changes


class ProrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.windows = {
            "sub-public": [{"plan": "starter", "start_day": 0, "end_day": 30}],
            "sub-denied": [{"plan": "starter", "start_day": 0, "end_day": 30}],
        }

    def test_authorized_upgrade_writes_matching_views(self) -> None:
        charges = ChargeWriter()
        entitlements = EntitlementStore(self.windows)
        authorizer = PlanEntitlement({"owner": {"sub-public": {"growth"}}})

        written = apply_plan_changes(
            charges,
            entitlements,
            authorizer,
            [PlanChange("sub-public", "owner", "growth", 10)],
        )

        self.assertEqual(1_600, written[0]["amount_cents"])
        self.assertEqual("growth", entitlements.current_plan("sub-public"))
        self.assertEqual(written, charges.rows)

    def test_denied_change_does_not_reach_storage(self) -> None:
        charges = ChargeWriter()
        entitlements = EntitlementStore(self.windows)
        authorizer = PlanEntitlement({"viewer": {"sub-denied": {"starter"}}})

        with self.assertRaises(EntitlementDenied):
            apply_plan_changes(
                charges,
                entitlements,
                authorizer,
                [PlanChange("sub-denied", "viewer", "scale", 12)],
            )

        self.assertEqual([], charges.rows)
        self.assertEqual(0, charges.write_calls)
        self.assertEqual(0, entitlements.write_calls)


if __name__ == "__main__":
    unittest.main()
