#!/usr/bin/env python3
"""Offline controls for independent confirmation fixtures. Writes only controls/."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
TASKS = ('CF-LEASE', 'CF-CONFIG')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=TASKS)
    args = parser.parse_args()
    controls = BASE / 'controls'
    controls.mkdir(exist_ok=True)
    scratch = controls / 'scratch'
    scratch.mkdir(exist_ok=True)
    prediction_file = BASE / 'predictions.json'
    predictions = json.loads(prediction_file.read_text())
    outcomes = []
    for name in (args.task,) if args.task else TASKS:
        task = BASE / name
        spec = json.loads((task / 'task.json').read_text())
        visible = task / 'visible'
        gold = task / 'gold'
        actual_visible = sorted('visible/' + path.relative_to(visible).as_posix() for path in visible.rglob('*') if path.is_file())
        assert spec['visible_files'] == actual_visible, 'visible inventory mismatch'
        for binding_group in json.loads((task / 'hidden' / 'manifests.json').read_text())['manifestations']:
            for binding in binding_group['contract_bindings']:
                source = task / binding['file']
                assert digest(source) == binding['sha256'], 'contract binding digest mismatch'
                assert binding['quote'] in source.read_text(), 'contract quote missing'
        expected_patch = ''
        for path in sorted(p.relative_to(visible).as_posix() for p in visible.rglob('*') if p.is_file()):
            before, after = (visible / path).read_text(), (gold / path).read_text()
            if before != after:
                assert path.endswith('.py') and not path.startswith('checks/'), 'reference must repair production source'
                expected_patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + path, tofile='b/' + path))
        assert (task / 'patches' / 'gold.patch').read_text() == expected_patch, 'patch/reference mismatch'
        expected_ids = [item['id'] for item in json.loads((task / 'hidden' / 'manifests.json').read_text())['manifestations']]
        with tempfile.TemporaryDirectory(dir=scratch, prefix=name + '-') as temporary:
            temp = Path(temporary)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(temp))
            for arm, source in [('baseline', visible), ('gold', gold)]:
                work = temp / arm
                shutil.copytree(source, work)
                for phase, command in [('public', [sys.executable, '-B', 'checks/run_checks.py']),
                                       ('hidden', [sys.executable, '-B', str(task / 'hidden' / 'oracle.py'), str(work)])]:
                    completed = subprocess.run(command, cwd=work, env=env, text=True, capture_output=True, timeout=60)
                    record = {'task': name, 'arm': arm, 'phase': phase, 'command': command,
                              'returncode': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr}
                    log = controls / f'{name}.{arm}.{phase}.json'
                    log.write_text(json.dumps(record, indent=2) + '\n')
                    assert completed.returncode == 0, f'{name} {arm} {phase} crashed; see {log}'
                    if phase == 'hidden':
                        data = json.loads(completed.stdout)
                        manifestations = data['manifestations']
                        assert [item['id'] for item in manifestations] == expected_ids, 'oracle/manifest mismatch'
                        observed = {item['id']: item['passed'] for item in manifestations}
                        expected = {key: True for key in expected_ids} if arm == 'gold' else predictions['tasks'][name]['baseline']
                        assert observed == expected, f'{name} {arm}: observed controls disagree with predictions; inspect raw log {log}'
                        record['passed'] = sum(observed.values())
                        record['total'] = len(observed)
                    outcomes.append({key: value for key, value in record.items() if key not in ('stdout', 'stderr', 'command')})
    summary = {'validated_at': datetime.now(timezone.utc).isoformat(), 'predictions_sha256': digest(prediction_file), 'outcomes': outcomes}
    (controls / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
