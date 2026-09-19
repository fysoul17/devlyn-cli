"""Reuse 0183 dispatch unchanged; primary owner never invokes resolve itself."""
from pathlib import Path
import importlib.util
import json
import os
import sys

R = Path(__file__).resolve().parents[3]
E = R / '.devlyn/0187'
S = R / '.git/devlyn-completion/2e0e0a6ae08ba22e8451fd57/scratch'
W = R.parent / '0187-participants'


def module(name):
    spec = importlib.util.spec_from_file_location('r0187_' + name, R / 'autoresearch/experiments/0183' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    result.EVIDENCE, result.SCRATCH, result.WORKS = E, S, W
    return result


def main():
    launch = module('launch')
    registry = json.loads((E / 'REGISTRATION.json').read_text())
    for row in registry['order']:
        if (E / 'runs' / row['draw'] / 'result.json').exists():
            continue
        before = dict(os.environ)
        try:
            sys.argv = ['launch.py', row['draw'], row['arm'], row['case']]
            launch.main()
        finally:
            os.environ.clear()
            os.environ.update(before)
        result = json.loads((E / 'runs' / row['draw'] / 'result.json').read_text())
        if result['error'] or not result['owned_writers_quiescent']:
            raise SystemExit('STOP: controller/cleanup failure; preserve row, inspect before subsequent draws')
    print('Registered workflow draws returned; external assessment remains required.', flush=True)


if __name__ == '__main__':
    main()
