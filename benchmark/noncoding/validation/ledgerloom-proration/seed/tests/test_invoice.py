import unittest

from billing.invoice import Invoice
from billing.plans import monthly_price_cents


class InvoiceTest(unittest.TestCase):
    def test_total_of_an_empty_invoice_is_zero(self):
        self.assertEqual(Invoice("acme").total_cents(), 0)

    def test_lines_add_up(self):
        invoice = Invoice("acme")
        invoice.add_line("Team plan", monthly_price_cents("team"))
        invoice.add_line("Starter plan", monthly_price_cents("starter"))
        self.assertEqual(invoice.total_cents(), 2998)
        self.assertIsInstance(invoice.total_cents(), int)

    def test_lines_keep_their_shape(self):
        invoice = Invoice("acme")
        invoice.add_line("Studio plan", 4900)
        self.assertEqual(invoice.lines, [("Studio plan", 4900)])

    def test_float_amounts_are_rejected(self):
        with self.assertRaises(TypeError):
            Invoice("acme").add_line("Team plan", 19.99)

    def test_render_shows_lines_and_total(self):
        invoice = Invoice("acme")
        invoice.add_line("Team plan", 1999)
        rendered = invoice.render()
        self.assertIn("Team plan", rendered)
        self.assertIn("$19.99", rendered)
        self.assertIn("TOTAL", rendered)


if __name__ == "__main__":
    unittest.main()
