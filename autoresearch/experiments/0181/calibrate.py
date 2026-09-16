"""Admit distinct valid solutions; reject seeds and isolated contract mutations."""
import argparse
import json
import shutil
import tempfile
from pathlib import Path
from score import BASE, score


def variants(case):
    calibration = BASE / case / 'calibration'
    module = 'overlay.py' if case == 'small' else 'async_map.py'
    reference = (calibration / 'reference.txt').read_text()
    yield 'seed', False, {}
    yield 'reference', True, {module: reference}
    yield 'alternative', True, {module: (calibration / 'alternative.txt').read_text()}
    if case == 'small':
        mutations = {
            'keep_deleted': ('target.pop(key, None)', 'target[key] = None'),
            'missing_delete_raises': ('target.pop(key, None)', 'target.pop(key)'),
            'replace_nested': ('if not isinstance(target.get(key), dict):', 'if True:'),
            'alias_and_tombstone': ('apply(target[key], value)', 'target[key] = value'),
            'reject_empty': ('apply(target[key], value)', 'apply(target[key], value)\n                if not target[key]:\n                    del target[key]'),
            'skip_earlier_validation': ('for layer in layers:\n        validate(layer)', 'for layer in layers[-1:]:\n        validate(layer)'),
            'accept_bad_keys': ('if not isinstance(key, str):', 'if False:'),
            'accept_bad_leaf': ('elif child is not None and not isinstance(child, str):', 'elif False:'),
        }
    else:
        mutations = {
            'bool_is_integer': ('isinstance(limit, bool) or not isinstance(limit, int)', 'not isinstance(limit, int)'),
            'wrong_limit_error': ("raise ValueError('limit must be positive')", "raise TypeError('limit must be positive')"),
            'eager_intake': ('iterator = iter(items)', 'iterator = iter(list(items))'),
            'over_limit': ('len(pending) < limit', 'len(pending) <= limit'),
            'head_of_line': ('return_when=asyncio.FIRST_COMPLETED', 'return_when=asyncio.ALL_COMPLETED'),
            'reverse_results': ('return result', 'return result[::-1]'),
            'wrapped_failure': ('result[pending[task]] = task.result()', "try:\n                    result[pending[task]] = task.result()\n                except Exception as error:\n                    raise RuntimeError('wrapped') from error"),
            'omit_cancel': ('task.cancel()', 'pass'),
            'omit_drain': ('await asyncio.shield(cleanup)', 'await asyncio.sleep(0)'),
            'unshielded_cleanup': ('await asyncio.shield(cleanup)', 'await cleanup'),
        }
    for name, (old, new) in mutations.items():
        if reference.count(old) != 1:
            raise ValueError('mutation must apply exactly once: ' + name)
        yield name, False, {module: reference.replace(old, new)}
    if case == 'hard':
        alternative = (calibration / 'alternative.txt').read_text()
        yield 'double_cancel_gather', False, {module: alternative.replace('await asyncio.shield(asyncio.gather(*tasks))', 'await asyncio.gather(*tasks)')}
    yield 'protected_bytes', False, {module: reference, 'NOTICE.txt': 'changed\n'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('refuse to overwrite calibration evidence')
    records = []
    with tempfile.TemporaryDirectory(prefix='calibration-', dir=args.scratch) as temporary:
        for case in ('small', 'hard'):
            for name, expected, replacements in variants(case):
                target = Path(temporary) / (case + '-' + name)
                shutil.copytree(BASE / case / 'seed', target)
                for relative, content in replacements.items():
                    (target / relative).write_text(content)
                result = score(case, target)
                records.append({'case': case, 'variant': name, 'expected_success': expected, **result})
                print(case, name, result['mechanical_success'], flush=True)
    args.output.write_text(json.dumps(records, indent=2) + '\n')
    if any(row['mechanical_success'] != row['expected_success'] for row in records):
        raise SystemExit('CALIBRATION FAILED: inspect raw checks; do not dispatch draws')
