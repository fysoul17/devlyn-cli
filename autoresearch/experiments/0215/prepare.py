"""Prepare the 0215 D1 B diagnostic cell with evaluator-parity color checks; never dispatch."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CHECKS = ['node --test tests/options.variadic.test.js', 'node --test']


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(runtime_path):
    cell = Path(subprocess.check_output([
        sys.executable, '-B', str(HERE.parent / '0214/prepare.py'), '1', str(Path(runtime_path).resolve()),
    ], text=True).strip())
    caller_path = cell / 'work/.devlyn/caller.json'
    caller = json.loads(caller_path.read_text())
    prompt = (cell / 'prompt.txt').read_text()
    old = json.dumps(caller, indent=2)
    if caller['public_checks'] != CHECKS or prompt.count(old) != 1:
        raise ValueError('upstream D1 caller contract changed; do not launch')
    caller['public_checks'] = ['env -u NO_COLOR ' + command for command in CHECKS]
    new = json.dumps(caller, indent=2)
    prompt = prompt.replace(old, new)
    plan = json.loads((cell / 'plan.json').read_text())
    baseline = json.loads((cell / 'baseline.json').read_text())
    pilot = json.loads((cell / 'pilot.json').read_text())
    caller_path.write_text(new)
    (cell / 'prompt.txt').write_text(prompt)
    plan['argv'][-1] = prompt
    baseline['prompt_sha256'] = digest(prompt)
    baseline['files']['.devlyn/caller.json'] = digest(new)
    pilot.update(treatment='0215 env -u NO_COLOR public checks',
                 prepare_0215_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (cell / 'plan.json').write_text(json.dumps(plan, indent=2))
    (cell / 'baseline.json').write_text(json.dumps(baseline, indent=2))
    (cell / 'pilot.json').write_text(json.dumps(pilot, indent=2))
    return cell


if __name__ == '__main__':
    print(prepare(sys.argv[1]))
