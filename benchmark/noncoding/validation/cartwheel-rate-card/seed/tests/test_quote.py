import unittest

from rates.quote import quote_cents, zone_labels


class QuoteTest(unittest.TestCase):
    def test_metro_two_kilograms(self):
        # 450 + 120 * 2 = 690 subtotal, plus the fuel surcharge.
        self.assertEqual(quote_cents("ZONE_A", 2), 731)

    def test_regional_zero_weight_is_base_plus_surcharge(self):
        self.assertEqual(quote_cents("ZONE_B", 0), 689)

    def test_result_is_integer_cents(self):
        self.assertIsInstance(quote_cents("ZONE_C", 5), int)

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            quote_cents("ZONE_Z", 1)

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            quote_cents("ZONE_A", -1)

    def test_zone_labels_cover_every_zone(self):
        labels = zone_labels()
        self.assertEqual(labels["ZONE_A"], "Metro")
        self.assertIn("ZONE_C", labels)


if __name__ == "__main__":
    unittest.main()
