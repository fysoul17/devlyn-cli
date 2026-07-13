import unittest

from rates.registry import CURRENCY, FUEL_SURCHARGE_PERCENT, ZONES


class RegistryTest(unittest.TestCase):
    def test_currency(self):
        self.assertEqual(CURRENCY, "USD")

    def test_every_zone_rule_is_complete(self):
        for key, rule in ZONES.items():
            self.assertIsInstance(key, str)
            self.assertEqual(
                sorted(rule), ["base_cents", "label", "per_kg_cents"], key
            )
            self.assertIsInstance(rule["base_cents"], int)
            self.assertIsInstance(rule["per_kg_cents"], int)

    def test_surcharge_is_a_whole_percent(self):
        self.assertIsInstance(FUEL_SURCHARGE_PERCENT, int)
        self.assertGreaterEqual(FUEL_SURCHARGE_PERCENT, 0)


if __name__ == "__main__":
    unittest.main()
