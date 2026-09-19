import unittest
from duration import parse_duration, format_duration


class DurationTests(unittest.TestCase):
    def test_units(self):
        for value, expected in [('12ms', 12), ('1.25s', 1250), ('2m', 120000), ('1h', 3600000), (' 000.001s\t', 1)]:
            with self.subTest(value=value):
                self.assertEqual(parse_duration(value), expected)
                self.assertIs(type(parse_duration(value)), int)

    def test_invalid(self):
        for value in ('-1s', '1e3ms', '1 s', '.5s', '1.s', '1S', '0.0001s', '１２s'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_duration(value)
        with self.assertRaises(TypeError):
            parse_duration(1000)

    def test_existing_format(self):
        self.assertEqual(format_duration(1001), '1001ms')
        self.assertEqual(format_duration(-1), '-1ms')


if __name__ == '__main__':
    unittest.main()
