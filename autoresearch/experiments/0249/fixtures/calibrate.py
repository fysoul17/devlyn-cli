"""Local deterministic calibration; never invokes models or changes source trees."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=ROOT / 'calibration')
OUT = parser.parse_args().output.resolve()
assert OUT.is_relative_to(ROOT), 'calibration output must stay in fixtures subtree'
PREDICTION = OUT / 'prediction.json'
assert PREDICTION.exists(), 'record predictions before execution'

def hashes(path):
    return {str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(path.rglob('*')) if file.is_file()}


def run_task(task):
    original = ROOT / task
    control = OUT / 'controls' / task
    if control.exists():
        raise RuntimeError('refusing to replace prior control')
    shutil.copytree(original / 'gold', control)
    module = control / ('folio/workspace.py' if task == 'OR1' else 'relay/loader.py')
    source = module.read_text()
    before, after = (
        ('self.documents[name] = deepcopy(document)', 'self.documents[name] = document') if task == 'OR1'
        else ('if not self._closed and self._pending.get(key) is task:', 'if not self._closed:'))
    assert source.count(before) == 1
    module.write_text(source.replace(before, after))
    rows = []
    for variant, target in [('baseline', original / 'visible'), ('gold', original / 'gold'), ('fault', control)]:
        for check in ('public', 'oracle'):
            name = f'{task}.{variant}.{check}'
            log = OUT / (name + '.json')
            if log.exists():
                raise RuntimeError('refusing to replace calibration result')
            command = ['python3', '-B', 'checks/run_checks.py'] if check == 'public' else ['python3', '-B', str(original / 'hidden/oracle.py'), str(target)]
            scratch = OUT / 'scratch' / name
            scratch.mkdir(parents=True)
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(scratch))
            pre_hash = hashes(target)
            start = datetime.now(timezone.utc).isoformat()
            result = subprocess.run(command, cwd=target, env=environment, text=True, capture_output=True, timeout=30)
            assert hashes(target) == pre_hash, 'evaluated source mutated'
            record = dict(command=command, cwd=str(target), started_at=start, ended_at=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr, source_sha256=pre_hash, source_unchanged=True, prediction_sha256=hashlib.sha256(PREDICTION.read_bytes()).hexdigest())
            log.write_text(json.dumps(record, indent=2) + '\n')
            parsed = json.loads(result.stdout.strip().splitlines()[-1])
            assert result.returncode == 0, record
            if check == 'public':
                assert parsed['public_passed'] is True
                rows.append(dict(task=task, variant=variant, check=check, passed=True, tests=parsed['tests']))
            else:
                rows.append(dict(task=task, variant=variant, check=check, passed=[row['id'] for row in parsed['manifestations'] if row['passed']], failed=[row['id'] for row in parsed['manifestations'] if not row['passed']]))
    return rows

with ThreadPoolExecutor(max_workers=2) as executor:
    results = list(executor.map(run_task, ['OR1', 'OR2']))
summary = {'completed_at': datetime.now(timezone.utc).isoformat(), 'results': [row for group in results for row in group]}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
