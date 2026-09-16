"""Run outside the submitted tree: python oracle.py SUBMISSION."""
import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from selection import parse_selection


class Contract(unittest.TestCase):
    def test_order(self):
        self.assertEqual(parse_selection('3, 1-2, 3'), [3, 1, 2])
        self.assertEqual(parse_selection('005-007,2,6,1-3'), [5, 6, 7, 2, 1, 3])

    def test_generated_valid(self):
        # Expected values come from token/value pairs, not the submitted parser.
        tokens = [('2', [2]), ('01-03', [1, 2, 3]), ('9-9', [9]), ('999', [999])]
        for size in (1, 2, 3):
            for choices in itertools.product(tokens, repeat=size):
                expected = list(dict.fromkeys(n for _, values in choices for n in values))
                text = ','.join(' \t' + token.replace('-', '\n-\t') + '\n' for token, _ in choices)
                with self.subTest(text=text):
                    self.assertEqual(parse_selection(text), expected)

    def test_empty(self):
        for text in ('', ' \t\n'):
            self.assertEqual(parse_selection(text), [])

    def test_invalid(self):
        for text in (',', '1,', ',1', '1,,2', '1, ,2', '3-1', '0', '00-1',
                     '1-0', '-1', '+1', '1-+2', '1.0', '1-2-3', '1--2',
                     '1-', '1- ', '-', '1 2', '١', '１', '1-٢', '\u00a01', '1\u00a0', '\r1', '\v', '\f2'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_selection(text)

    def test_type(self):
        for value in (None, 1, True, [], {}, b'1'):
            with self.subTest(value=value), self.assertRaises(TypeError):
                parse_selection(value)


if __name__ == '__main__':
    unittest.main()
