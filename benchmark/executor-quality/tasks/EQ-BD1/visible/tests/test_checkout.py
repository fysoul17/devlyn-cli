import unittest

from checkout import format_option
from rates import Quote


class CheckoutFormattingTests(unittest.TestCase):
    def test_formats_a_normalized_quote(self):
        quote = Quote(service_code="ground", eta_days=5, price_cents=799)
        self.assertEqual(
            format_option(quote),
            {"service_code": "ground", "eta_days": 5, "price_cents": 799},
        )


if __name__ == "__main__":
    unittest.main()
