import unittest

from rates import Quote, parse_quote


class ParseQuoteTests(unittest.TestCase):
    def test_parses_carrier_fields(self):
        self.assertEqual(
            parse_quote({"service_code": "air", "eta_days": "2", "price_cents": "1299"}),
            Quote(service_code="air", eta_days=2, price_cents=1299),
        )


if __name__ == "__main__":
    unittest.main()
