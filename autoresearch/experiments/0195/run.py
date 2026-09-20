"""Bounded 0195 comparison using unchanged 0193/0191 native transport."""
from pathlib import Path
import hashlib
import json
import runpy
import shutil
import subprocess
import sys
import tempfile

assert Path(sys.executable).samefile('/opt/homebrew/bin/python3'), 'Use the registered interpreter'
R = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent
E = R / '.devlyn/0195'
S = R / '.git/devlyn-completion/38e2e28ebf13803f20549c54/scratch'
W = R.parent / '0195-participants'
legacy = runpy.run_path(str(R / 'autoresearch/experiments/0193/run.py'))
hashes, module, put = (legacy[name] for name in ('hashes', 'module', 'put'))


def calibrate():
    original = (E / 'inputs/root/package/terminal-claim-check.py').read_text()
    old = '        if verdict not in VALID_VERIFY_VERDICTS:'
    assert original.count(old) == 1
    reference = original.replace(old, '        if not isinstance(verdict, str) or verdict not in VALID_VERIFY_VERDICTS:')
    variants = dict(original=original, reference=reference,
        rejects_null=reference.replace('        if verdict is None:', '        if False:'),
        accepts_collections=reference.replace('not isinstance(verdict, str) or verdict not in VALID_VERIFY_VERDICTS',
                                             'isinstance(verdict, str) and verdict not in VALID_VERIFY_VERDICTS'),
        accepts_unknown=reference.replace('not isinstance(verdict, str) or verdict not in VALID_VERIFY_VERDICTS',
                                         'not isinstance(verdict, str)'))
    expected = dict(original={f'invalid/{i}/{a}' for i in range(4) for a in (False, True)}
                    | {'cli/0', 'cli/1', 'run-set/include'}, reference=set(),
                    rejects_null={'null/False', 'null/True'},
                    accepts_collections={f'invalid/{i}/{a}' for i in range(8) for a in (False, True)}
                    | {'cli/0', 'cli/1', 'run-set/include'},
                    accepts_unknown={f'invalid/{i}/{a}' for i in (8, 9) for a in (False, True)})
    results = []
    checker = runpy.run_path(str(H / 'check.py'))['check']
    for name, source in variants.items():
        with tempfile.TemporaryDirectory(dir=S) as raw:
            root = Path(raw)
            package = root / 'package'
            shutil.copytree(E / 'inputs/root/package', package)
            (package / 'terminal-claim-check.py').write_text(source)
            rows = checker(package, root)
        failures = {row['check'] for row in rows if not row['passed']}
        results.append(dict(variant=name, rows=rows, expected=sorted(expected[name])))
        if failures != expected[name]:
            (E / 'CALIBRATION-FAILED.json').write_text(json.dumps(results, indent=2) + '\n')
            raise AssertionError((name, failures ^ expected[name]))
    legacy['put'](E / 'CALIBRATION.json', results)
    (E / 'reference.py').write_text(reference)
    print(json.dumps({r['variant']: sum(v['passed'] for v in r['rows']) for r in results}))


def freeze():
    for path in (E / 'inputs/root/package').iterdir():
        assert path.read_bytes() == (R / 'config/skills/_shared' / path.name).read_bytes()
    paths = [*[p for p in H.iterdir() if p.is_file()],
        *[p for p in (E / 'inputs').rglob('*') if p.is_file()],
        E / 'models_cache.json', E / 'CALIBRATION.json', E / 'reference.py', E / 'REPRODUCTION.json',
        R / '.devlyn/0179/catalog-setting.txt', R / 'autoresearch/experiments/0179/AGENTS.candidate.md',
        R / 'autoresearch/experiments/0193/run.py', R / 'autoresearch/experiments/0191/launch.py',
        R / 'autoresearch/scripts/comparison-controller.py', R / 'config/skills/_shared/run-bounded.py',
        R / 'config/skills/_shared/task-complete.py', R / 'config/skills/_shared/platform-support.py']
    legacy['put'](E / 'REGISTRATION.json', dict(
        interpreter=dict(path=sys.executable, version=sys.version),
        version=subprocess.check_output(['codex', '--version'], text=True).strip(),
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
        order=[dict(draw=f'{i:02}-{arm}', arm=arm, case='root') for i, arm in enumerate('ABBA', 1)],
        sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        legacy['run'].__globals__.update(E=E, S=S, W=W)
        legacy['run']()
    else:
        {'calibrate': calibrate, 'freeze': freeze}[sys.argv[1]]()
