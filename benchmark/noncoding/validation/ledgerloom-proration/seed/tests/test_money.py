import unittest

from billing.money import format_cents, round_half_up


class RoundHalfUpTest(unittest.TestCase):
    def test_ties_round_away_from_zero(self):
        self.assertEqual(round_half_up(5, 2), 3)
        self.assertEqual(round_half_up(125, 2), 63)
        self.assertEqual(round_half_up(-5, 2), -3)

    def test_rounds_to_the_nearest_whole_unit(self):
        self.assertEqual(round_half_up(1, 3), 0)
        self.assertEqual(round_half_up(2, 3), 1)
        self.assertEqual(round_half_up(9990, 30), 333)

    def test_result_is_an_int(self):
        self.assertIsInstance(round_half_up(7, 2), int)

    def test_rejects_non_int_input(self):
        with self.assertRaises(TypeError):
            round_half_up(5.0, 2)

    def test_rejects_non_positive_denominator(self):
        with self.assertRaises(ValueError):
            round_half_up(5, 0)


class FormatCentsTest(unittest.TestCase):
    def test_formats_dollars_and_cents(self):
        self.assertEqual(format_cents(1234), "$12.34")
        self.assertEqual(format_cents(5), "$0.05")
        self.assertEqual(format_cents(-250), "-$2.50")

    def test_rejects_floats(self):
        with self.assertRaises(TypeError):
            format_cents(12.34)


if __name__ == "__main__":
    unittest.main()
