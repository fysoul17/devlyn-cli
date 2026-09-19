"""External requirement checks, run only on copied products after output sealing."""
import importlib.util
import json
from pathlib import Path
import sys
import tracemalloc
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(sys.argv[1]) / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Duration(unittest.TestCase):
    def test_exact_boundaries(self):
        f = load('duration').parse_duration
        for text, expected in [('9223372036854775807ms', 2**63-1),
                               ('9223372036854775.807s', 2**63-1),
                               ('0.00005m', 3), ('0.0000025h', 9), ('000.000ms', 0)]:
            self.assertEqual(f(text), expected, text)
            self.assertIs(type(f(text)), int)
        for text in ('9223372036854775808ms', '9223372036854775.808s', '0.0000001h'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                f(text)

    def test_grammar(self):
        f = load('duration').parse_duration
        for text in ('1s\n2s', '1s!', '1_000s', '+1s', '1.s', '.1s', '1.2.3s',
                     '1\u00a0s', '\u00a01s', '1s\u00a0', '\x0b1s', '\r1s', '١s', '', 'ms'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                f(text)
        for value in (None, 1, True, b'1s', [], {}):
            with self.subTest(value=value), self.assertRaises(TypeError):
                f(value)
        self.assertEqual(f('\t\n 1.000s \t\n'), 1000)

    def test_preserve_format(self):
        f = load('duration').format_duration
        for x in (-1, 0, 999, 2**63, True, 'text'):
            self.assertEqual(f(x), str(x) + 'ms')


class Stream(unittest.TestCase):
    def test_partition_invariance(self):
        m = load('stream')
        payload = ' \t\r\n{"k":"雪"}\r\n[1,null]\ntrue\nfalse\n"NaN"\n12.5\n0'.encode()
        expected = [{'k': '雪'}, [1, None], True, False, 'NaN', 12.5, 0]
        for width in (1, 2, 3, 7, len(payload)):
            d = m.Decoder()
            got = []
            for i in range(0, len(payload), width):
                got.extend(d.feed(payload[i:i+width]))
            self.assertEqual(got + d.finish(), expected)
            self.assertEqual(d.finish(), [])
            with self.assertRaises(RuntimeError):
                d.feed(b'')
            with self.assertRaises(RuntimeError):
                d.feed(None)

    def test_sticky_failure_precedence(self):
        m = load('stream')
        for payload, reason in [(b'\n1\n\xff\n', 'utf8'), (b'\n1\nNaN\n', 'json'),
                                (b'\n1\nInfinity\n', 'json'), (b'\n1\n-Infinity\n', 'json'),
                                (b'\n1\n[NaN]\n', 'json'), (b'\n1\n{\n', 'json')]:
            d = m.Decoder()
            with self.assertRaises(m.ParseError) as caught:
                d.feed(payload)
            error = caught.exception
            self.assertEqual((error.line, error.reason), (3, reason))
            for call in (lambda: d.feed(b''), lambda: d.feed(b'1\n'), lambda: d.feed(None), d.finish):
                with self.assertRaises(m.ParseError) as repeated:
                    call()
                self.assertIs(repeated.exception, error)

    def test_limits_and_error_order(self):
        m = load('stream')
        for value in (True, False, 1.5, '2', None):
            with self.assertRaises(TypeError):
                m.Decoder(value)
        for value in (0, -1):
            with self.assertRaises(ValueError):
                m.Decoder(value)
        self.assertEqual(m.Decoder(3).feed(b'1\r\n'), [1])
        self.assertEqual(m.Decoder(1).feed(b'1\n'), [1])
        for parts, line, reason in [([b'1\r\n'], 1, 'limit'), ([b' ', b' '], 1, 'limit'),
                                    ([b'1\n', b'\xff\xff\n'], 2, 'limit'),
                                    ([b'{\n111\n'], 1, 'json')]:
            d = m.Decoder(1)
            with self.assertRaises(m.ParseError) as caught:
                for part in parts:
                    d.feed(part)
            self.assertEqual((caught.exception.line, caught.exception.reason), (line, reason))

    def test_finish_and_type_recovery(self):
        m = load('stream')
        d = m.Decoder()
        self.assertEqual(d.feed(b'"a'), [])
        for value in ('"', bytearray(b'"'), None):
            with self.assertRaises(TypeError):
                d.feed(value)
        self.assertEqual(d.feed(b'"'), [])
        self.assertEqual(d.finish(), ['a'])
        for payload, reason in [(b'\n{', 'json'), (b'\n\xe9', 'utf8')]:
            d = m.Decoder()
            self.assertEqual(d.feed(payload), [])
            with self.assertRaises(m.ParseError) as caught:
                d.finish()
            self.assertEqual((caught.exception.line, caught.exception.reason), (2, reason))
            with self.assertRaises(m.ParseError) as again:
                d.finish()
            self.assertIs(caught.exception, again.exception)
        self.assertEqual(m.Decoder().finish(), [])
        d = m.Decoder()
        self.assertEqual(d.feed(b' \t\r'), [])
        self.assertEqual(d.finish(), [])

    def test_independence_and_retained_memory(self):
        m = load('stream')
        a, b = m.Decoder(16), m.Decoder(16)
        first = a.feed(b'{"a":[]}\n')[0]
        b.feed(b'"other')
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        chunk = b'0\n' * 4096
        for _ in range(128):
            values = a.feed(chunk)
            self.assertEqual(len(values), 4096)
        del values
        retained = tracemalloc.get_traced_memory()[0] - baseline
        tracemalloc.stop()
        self.assertLess(retained, 131072, 'processed input retained (1 MiB corpus, 128 KiB allowance)')
        self.assertEqual(first, {'a': []})
        self.assertEqual(b.feed(b'"\n'), ['other'])
        self.assertEqual(a.finish(), [])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Duration if sys.argv[2] == 'root' else Stream)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
