import unittest

from transport import decode_items


class TransportTests(unittest.TestCase):
    def test_decodes_catalog_items(self):
        self.assertEqual(
            decode_items('{"items": [{"sku": "lamp"}]}'),
            [{"sku": "lamp"}],
        )


if __name__ == "__main__":
    unittest.main()
