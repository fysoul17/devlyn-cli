"""Validate named oracle failure modes before any workflow participant launch."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

R = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent
E = R / '.devlyn/0187'
S = R / '.git/devlyn-completion/2e0e0a6ae08ba22e8451fd57/scratch'


def main():
    mutations = {
        'root': [
            ('unicode-whitespace', 'text.strip(" \\t\\n")', 'text.strip()'),
            ('float-rounding', 'result, remainder = divmod(numerator, 10 ** len(fraction))',
             'result, remainder = int(numerator / 10 ** len(fraction)), 0'),
            ('overflow-accepted', 'if remainder or result > 2**63-1:', 'if remainder:')],
        'filter': [
            ('nonstandard-json', 'json.loads(text, parse_constant=reject_constant)', 'json.loads(text)'),
            ('nonsticky', 'if self.error is not None:', 'if False:'),
            ('blank-line-count', 'self.line += 1', 'self.line += 0'),
            ('unbounded-line', 'if len(self.buffer) + stop - offset > self.max_line_bytes:', 'if False:'),
            ('retain-history', 'values = []\n        offset = 0',
             'self.history = getattr(self, "history", b"") + chunk\n        values = []\n        offset = 0')]
    }
    rows = []
    for case, name in [('root', 'duration'), ('filter', 'stream')]:
        reference = (E / 'source' / (name + '.py')).read_text()
        variants = [('original', (E / 'inputs' / case / (name + '.py')).read_text(), False),
                    ('reference', reference, True)]
        for label, old, new in mutations[case]:
            assert old in reference, label
            variants.append((label, reference.replace(old, new), False))
        for label, source, expected in variants:
            with tempfile.TemporaryDirectory(prefix='0187-cal-', dir=S) as temporary:
                work = Path(temporary)
                (work / (name + '.py')).write_text(source)
                p = subprocess.run([sys.executable, '-B', str(H / 'heldout.py'), str(work), case],
                                   capture_output=True, timeout=90)
                stem = E / ('calibration-' + name + '-' + label)
                stem.with_suffix('.stdout').write_bytes(p.stdout)
                stem.with_suffix('.stderr').write_bytes(p.stderr)
                rows.append({'case': case, 'control': label, 'expected_pass': expected, 'exit_code': p.returncode})
    (E / 'CALIBRATION.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows), flush=True)
    assert all((row['exit_code'] == 0) == row['expected_pass'] for row in rows)


if __name__ == '__main__':
    main()
