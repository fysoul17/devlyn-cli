"""Observable examples, invalid types and dictionary identity checks."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('submission', Path(sys.argv.pop(1)) / 'overlay.py')
submission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submission)
merge = submission.merge_layers


class Contract(unittest.TestCase):
    def test_values(self):
        cases = [
            ([], {}),
            ([{}], {}),
            ([{'a': '1'}, {'a': '2'}], {'a': '2'}),
            ([{'a': '1'}, {'a': None}], {}),
            ([{'a': None}], {}),
            ([{'a': {}}], {'a': {}}),
            ([{'a': {'b': '1'}}, {'a': {}}], {'a': {'b': '1'}}),
            ([{'a': {'b': '1', 'c': '2'}}, {'a': {'b': None}}], {'a': {'c': '2'}}),
            ([{'a': {'b': '1'}}, {'a': {'b': None}}], {'a': {}}),
            ([{'a': '1'}, {'a': {'b': None}}], {'a': {}}),
            ([{'a': {'b': '1'}}, {'a': '2'}], {'a': '2'}),
            ([{'a': {'b': '1'}}, {'a': None}, {'a': {'c': '2'}}], {'a': {'c': '2'}}),
            ([{'a': {'b': {'c': '1'}}}, {'a': {'b': {'c': None, 'd': '2'}}}], {'a': {'b': {'d': '2'}}}),
            ([{'': '', '한': {'키': '값'}}, {'한': {'키': None}}], {'': '', '한': {}}),
        ]
        for layers, expected in cases:
            with self.subTest(layers=layers):
                before = copy.deepcopy(layers)
                self.assertEqual(merge(*layers), expected)
                self.assertEqual(layers, before)

    def test_invalid_even_if_overwritten(self):
        for layer in [None, [], [('a', 'b')], 'bad', 1, True]:
            with self.subTest(layer=layer), self.assertRaises(TypeError):
                merge(layer)
        for bad in [0, False, 1.5, [], ['x'], (), object()]:
            for replacement in [None, 'ok', {}]:
                for layer in [{'a': bad}, {'a': {'deep': bad}}]:
                    with self.subTest(bad=bad, replacement=replacement), self.assertRaises(TypeError):
                        merge(layer, {'a': replacement})
        for bad_key in [0, None, ('x',), False]:
            for layer in [{bad_key: 'x'}, {'a': {bad_key: 'x'}}]:
                with self.subTest(key=bad_key), self.assertRaises(TypeError):
                    merge(layer, {'a': None})

    def test_no_aliases(self):
        shared = {'inner': {'leaf': 'x'}, 'deleted': None}
        source = {'a': shared, 'b': shared}
        before = copy.deepcopy(source)
        result = merge(source, {'a': {'inner': {'new': 'y'}}})
        self.assertEqual(result, {'a': {'inner': {'leaf': 'x', 'new': 'y'}}, 'b': {'inner': {'leaf': 'x'}}})
        self.assertEqual(source, before)
        dictionaries = []
        def visit(value):
            if isinstance(value, dict):
                dictionaries.append(value)
                for child in value.values():
                    visit(child)
        visit(result)
        self.assertEqual(len({id(value) for value in dictionaries}), len(dictionaries))
        result['a']['inner']['leaf'] = 'changed'
        self.assertEqual(source, before)
        self.assertEqual(result['b']['inner']['leaf'], 'x')
        self.assertIsNot(merge(source), merge(source))

    def test_depth_and_invalid_preservation(self):
        value = 'v'
        for _ in range(30):
            value = {'x': value}
        self.assertEqual(merge(value), value)
        original = {'nested': {'a': '1'}}
        with self.assertRaises(TypeError):
            merge(original, {'nested': {'a': '2', 'bad': []}})
        self.assertEqual(original, {'nested': {'a': '1'}})


if __name__ == '__main__':
    unittest.main()
