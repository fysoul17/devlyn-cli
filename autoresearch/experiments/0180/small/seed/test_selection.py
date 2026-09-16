import unittest
from selection import parse_selection


class LegacyTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(parse_selection('1,2,3'), [1, 2, 3])

    def test_range(self):
        self.assertEqual(parse_selection('1-3'), [1, 2, 3])

    def test_empty(self):
        self.assertEqual(parse_selection(''), [])


if __name__ == '__main__':
    unittest.main()
