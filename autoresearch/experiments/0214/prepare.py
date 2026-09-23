"""Prepare one exposed-material diagnostic cell; never dispatch a model."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def prepare(index, runtime_path):
    runtime_path = Path(runtime_path).resolve()
    runtime = json.loads(runtime_path.read_text())
    pilot_id = runtime['pilot_id']
    if index not in (0, 1) or not pilot_id or Path(runtime['output']).name != pilot_id:
        raise ValueError('D1 indices 0/1 require a pilot_id matching the distinct output directory name')
    cell = Path(subprocess.check_output([
        sys.executable, '-B', str(HERE.parent / '0211/prepare.py'),
        str(index), str(runtime_path),
    ], text=True).strip())
    original = (cell / 'prompt.txt').read_text()
    common = (HERE.parent / '0211/common.txt').read_text()
    plan = json.loads((cell / 'plan.json').read_text())
    baseline = json.loads((cell / 'baseline.json').read_text())
    if not original.startswith(common) or plan['argv'][-1] != original:
        raise ValueError('upstream common-prefix or embedded-prompt contract changed; do not launch')
    prompt = common + '\n\n' + (HERE / 'common-wait.txt').read_text() + original[len(common):]
    plan['argv'][-1] = prompt
    baseline['prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
    (cell / 'prompt.txt').write_text(prompt)
    (cell / 'plan.json').write_text(json.dumps(plan, indent=2))
    (cell / 'baseline.json').write_text(json.dumps(baseline, indent=2))
    (cell / 'pilot.json').write_text(json.dumps({
        'pilot_id': pilot_id, 'entry': baseline['entry'],
        'prepare_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'wait_sha256': hashlib.sha256((HERE / 'common-wait.txt').read_bytes()).hexdigest(),
        'purpose': 'exposed-material diagnostic; excluded from 0213 and advancement',
    }, indent=2))
    return cell


if __name__ == '__main__':
    print(prepare(int(sys.argv[1]), sys.argv[2]))
