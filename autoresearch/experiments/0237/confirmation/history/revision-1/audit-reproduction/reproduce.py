"""Reproduce two independent pre-revision confirmation oracle/test defects; no model calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parent
print((BASE / 'prediction.json').read_text(), end='')
results = []
for canonical_tmp in (False, True):
    with tempfile.TemporaryDirectory(prefix='0237-oracle-audit-') as temporary:
        temp = Path(temporary).resolve()
        work = temp / 'source'
        shutil.copytree(BASE / 'gold-original', work)
        document = work / 'beacon/document.py'
        source = document.read_text()
        before = "path.read_text(encoding='utf-8')"
        after = "path.read_bytes().decode('utf-8')"
        assert source.count(before) == 1
        document.write_text(source.replace(before, after))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        if canonical_tmp:
            env['TMPDIR'] = str(temp)
        for phase, command in [('public', [sys.executable, '-B', 'checks/run_checks.py']),
                               ('hidden', [sys.executable, '-B', str(BASE / 'oracle-original.py'), str(work)])]:
            completed = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=30)
            record = dict(canonical_tmp=canonical_tmp, phase=phase, command=command,
                          returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
            results.append(record)
            print(json.dumps(record), flush=True)
(BASE / 'raw-results.json').write_text(json.dumps(results, indent=2) + '\n')
for record in results:
    if record['phase'] == 'hidden':
        failures = [row['id'] for row in json.loads(record['stdout'])['manifestations'] if not row['passed']]
        assert failures == ['shared-file-once-per-load'], failures
    elif record['canonical_tmp']:
        assert record['returncode'] == 0, record
print('RESULT: method-specific oracle false negative reproduced with passing public checks. Raw default TMPDIR checks preserve separate platform-path failure.')
