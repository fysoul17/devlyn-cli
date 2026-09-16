"""Reject the seed and isolated contract defects; admit distinct valid solutions."""
import argparse
import json
import shutil
import tempfile
from pathlib import Path
from score import BASE, score


def variants(case):
    calibration = BASE / case / 'calibration'
    module = 'selection.py' if case == 'small' else 'store.py'
    reference = (calibration / 'reference.txt').read_text()
    files = {module: reference}
    if case == 'hard':
        files['cli.py'] = (calibration / 'cli-reference.txt').read_text()
    yield 'seed', False, {}
    yield 'reference', True, files
    yield 'alternative', True, {**files, module: (calibration / 'alternative.txt').read_text()}
    if case == 'small':
        mutations = {
            'sorted_order': ('return result', 'return sorted(result)'),
            'unicode_digits': ('[0-9]', r'\d'),
            'unicode_space': ('for token in text.split', "text = text.strip()\n    for token in text.split"),
            'zero': ('start < 1', 'start < 0'),
            'descending': ('or end < start', ''),
            'duplicates': ('if number not in result:', 'if True:'),
            'wrong_type': ("raise TypeError('text must be a string')", "raise ValueError('text must be a string')"),
        }
    else:
        mutations = {
            'partial_commit': ('inserted += 1', 'inserted += 1\n            connection.commit()'),
            'silent_conflict': ("raise ValueError('conflicting id')", 'continue'),
            'key_order_identity': ("json.loads(old[0]) != event['payload']", "old[0] != json.dumps(event['payload'])"),
            'invalid_values': ('isinstance(v, str)', 'True'),
            'extra_fields': ("set(event) != {'id', 'payload'}", "not {'id', 'payload'} <= set(event)"),
            'wrong_count': ('return inserted', 'return 0'),
            'reverse_order': ('ORDER BY seq', 'ORDER BY seq DESC'),
        }
    for name, (old, new) in mutations.items():
        if old not in reference:
            raise ValueError('mutation did not apply: ' + name)
        yield name, False, {**files, module: reference.replace(old, new)}
    if case == 'hard':
        for name, old, new in (
            ('cli_wrong_exit', 'return 2', 'return 0'),
            ('cli_stdout_error', 'file=sys.stderr', 'file=sys.stdout'),
            ('cli_multiline_error', "' '.join(str(error).splitlines())", 'str(error)'),
            ('cli_accept_object', 'if not isinstance(events, list):', 'if False:'),
        ):
            yield name, False, {**files, 'cli.py': files['cli.py'].replace(old, new)}
    yield 'protected_bytes', False, {**files, 'NOTICE.txt': 'changed\n'}


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
