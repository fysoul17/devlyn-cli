"""External requirement witnesses, not visible to repair participants."""
from pathlib import Path
import copy
import importlib.util
import json
import sys


def checks(case, product):
    results = {}

    def check(name, fn):
        try:
            fn()
        except Exception as exc:
            results[name] = {'pass': False, 'error': repr(exc)}
        else:
            results[name] = {'pass': True}

    def equal(actual, expected):
        assert actual == expected, (actual, expected)

    if case == 'template':
        expand = product.expand
        cases = {
            'closure': ('Hi ${absent}!', {}, 'Hi ${absent}!'),
            'false_review': ('${a}', {'a': '${b}', 'b': 'ok'}, '${b}'),
            'empty_name': ('${}/${z}', {'': ''}, '/${z}'),
            'escape_order': ('$${x}$$$${y}$$${x}', {'x': 'X'}, '${x}$${y}$X'),
            'adjacent_unicode': ('${한}${z}${한}', {'한': '字'}, '字${z}字'),
            'literals': ('x$|${open|${}', {}, 'x$|${open|${}'),
            'unclosed': ('${x}${', {'x': 'X'}, 'X${'),
            'unclosed_name': ('a${b', {'b': 'X'}, 'a${b'),
            'empty': ('', {}, ''),
            'large': ('${x}' * 1024, {'x': 'a' * 256}, 'a' * 262144),
        }
        for name, (text, values, expected) in cases.items():
            check(name, lambda t=text, v=values, e=expected: equal(expand(t, v), e))

        def preserved():
            values = {'x': '$$${x}', '': 'zero'}
            before = copy.deepcopy(values)
            equal(expand('${x}${}', values), '$$${x}zero')
            equal(values, before)
        check('input_preserved', preserved)
    else:
        cls = product.Inventory
        event = lambda n: {'kind': 'adjust', 'sku': 'a', 'quantity': n}

        def closure():
            item = cls({'a': 4})
            equal(item.apply([{'kind': 'metadata', 'sku': [], 'quantity': True}, event(2)]), {'a': 6})
            equal(item.undo(), {'a': 4})
            equal(cls({}).apply([{'kind': ''}] * 128), {})
        check('closure', closure)

        def false_review():
            for batch in ([], [event(1), event(-1)]):
                item = cls({'a': 4})
                item.apply([event(2)])
                equal(item.apply(batch), {'a': 6})
                equal(item.undo(), {'a': 6})
                equal(item.undo(), None)
        check('false_review', false_review)

        def unknown_no_op():
            item = cls({'a': 4})
            item.apply([event(2)])
            equal(item.apply([{'kind': 'note'}]), {'a': 6})
            equal(item.undo(), {'a': 6})
            equal(item.undo(), None)
        check('unknown_no_op', unknown_no_op)

        def failed_batch():
            invalid = [event(-8), event(True), event(1001), event(1.0),
                       {'kind': 'adjust'}, {'kind': 'adjust', 'sku': 'missing', 'quantity': 1}]
            for bad in invalid:
                item = cls({'a': 4})
                item.apply([event(2)])
                try:
                    item.apply([event(1), bad, event(7)])
                except ValueError:
                    pass
                else:
                    raise AssertionError(('invalid batch accepted', bad))
                equal(item.snapshot(), {'a': 6})
                equal(item.undo(), {'a': 4})
        check('atomic_failure_and_undo', failed_batch)

        def copies():
            initial = {'a': 4}
            batch = [event(2)]
            before = copy.deepcopy(batch)
            item = cls(initial)
            initial['a'] = 100
            result = item.apply(batch)
            result['a'] = 101
            snapshot = item.snapshot()
            snapshot['a'] = 102
            equal(item.snapshot(), {'a': 6})
            equal(batch, before)
            restored = item.undo()
            restored['a'] = 103
            equal(item.snapshot(), {'a': 4})
        check('copies_and_input_preservation', copies)

        def boundaries():
            item = cls({'a': 1000000})
            try:
                item.apply([event(1), event(-1)])
            except ValueError:
                pass
            else:
                raise AssertionError('intermediate overflow accepted')
            equal(item.snapshot(), {'a': 1000000})
            equal(item.undo(), None)
            equal(item.apply([event(-1000)]), {'a': 999000})
            equal(item.apply([event(1000)]), {'a': 1000000})
        check('domain_boundaries', boundaries)
    return results


def main():
    case, root = sys.argv[1], Path(sys.argv[2])
    spec = importlib.util.spec_from_file_location('product', root / 'product.py')
    product = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(product)
        result = checks(case, product)
    except Exception as exc:
        result = {'import': {'pass': False, 'error': repr(exc)}}
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if all(row['pass'] for row in result.values()) else 1)


if __name__ == '__main__':
    main()
