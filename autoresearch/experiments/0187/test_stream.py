import unittest
from stream import Decoder, ParseError


class StreamTests(unittest.TestCase):
    def test_chunks(self):
        d = Decoder()
        self.assertEqual(d.feed(b'{"x":'), [])
        self.assertEqual(d.feed(b'1}\nnull\n'), [{'x': 1}, None])
        self.assertEqual(d.feed(b'true'), [])
        self.assertEqual(d.finish(), [True])
        self.assertEqual(d.finish(), [])

    def test_utf8_crlf(self):
        d = Decoder()
        self.assertEqual(d.feed(b' \r\n"\xe9'), [])
        self.assertEqual(d.feed(b'\x9b\xaa"\r\n'), ['雪'])

    def test_error_location(self):
        d = Decoder()
        with self.assertRaises(ParseError) as caught:
            d.feed(b'\n1\n{\n')
        self.assertEqual((caught.exception.line, caught.exception.reason), (3, 'json'))

    def test_limit(self):
        with self.assertRaises(ParseError) as caught:
            Decoder(3).feed(b'1234')
        self.assertEqual((caught.exception.line, caught.exception.reason), (1, 'limit'))


if __name__ == '__main__':
    unittest.main()
