"""Prepare one registered 0219 cell: 0218 preparation plus Click owner/evaluator check parity; never dispatch."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LESS = 'env PATH=/control/less/usr/bin:"$PATH" '
FULL = 'python -m pytest'
PARITY = {
    'D2': {'python -m pytest tests/test_exceptions.py tests/test_basic.py':
           LESS + 'python -m pytest tests/test_exceptions/ tests/test_basic.py', FULL: LESS + FULL},
    'D4': {'python -m pytest tests/test_basic.py': LESS + 'python -m pytest tests/test_basic.py', FULL: LESS + FULL},
}

spec = importlib.util.spec_from_file_location('prepare0218', HERE.parent / '0218/prepare.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def prepare(index, runtime_path):
    cell = base.prepare(index, runtime_path)
    baseline = json.loads((cell / 'baseline.json').read_text())
    task = baseline['task']['id']
    pilot = json.loads((cell / 'pilot.json').read_text())
    pilot['parity_prepare_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if task in PARITY:
        caller_path = cell / 'work/.devlyn/caller.json'
        caller = json.loads(caller_path.read_text())
        prompt = (cell / 'prompt.txt').read_text()
        plan = json.loads((cell / 'plan.json').read_text())
        old = json.dumps(caller, indent=2)
        pytest = [c for c in caller['public_checks'] if c.startswith('python -m pytest')]
        if plan['argv'][-1] != prompt or prompt.count(old) != 1 or pytest != list(PARITY[task]):
            raise ValueError('upstream 0218 contract changed; do not launch')
        caller['public_checks'] = [PARITY[task].get(c, c) for c in caller['public_checks']]
        new = json.dumps(caller, indent=2)
        prompt = prompt.replace(old, new)
        caller_path.write_text(new)
        (cell / 'prompt.txt').write_text(prompt)
        plan['argv'][-1] = prompt
        baseline['prompt_sha256'] = base.digest(prompt)
        baseline['files']['.devlyn/caller.json'] = base.digest(new)
        (cell / 'plan.json').write_text(json.dumps(plan, indent=2))
        (cell / 'baseline.json').write_text(json.dumps(baseline, indent=2))
    (cell / 'pilot.json').write_text(json.dumps(pilot, indent=2))
    return cell


if __name__ == '__main__':
    print(prepare(int(sys.argv[1]), sys.argv[2]))
