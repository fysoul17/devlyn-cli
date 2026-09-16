import unittest
from overlay import merge_layers


class Legacy(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_layers(), {})

    def test_replace(self):
        self.assertEqual(merge_layers({'host': 'a'}, {'host': 'b'}), {'host': 'b'})

    def test_disjoint(self):
        self.assertEqual(merge_layers({'a': '1'}, {'b': '2'}), {'a': '1', 'b': '2'})
