"""Owner-directed direct run (2026-10-21): cells.tsv in order via run_cell.py, no floor reserve.

Stops (for the driver to resume) when seven-day use reaches 97%, the token has under 6300 s, or a cell returns STOP.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

L = Path('/Users/aipalm/.local/share/nx01/0256-live')
R = Path('/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-run/autoresearch/experiments/0256')
OUT = L / 'output'
LOG = OUT / 'driver.log'


def log(**fields):
    fields = dict(at=time.strftime('%Y-%m-%dT%H:%M:%S%z'), source='direct_run', **fields)
    with LOG.open('a') as stream:
        stream.write(json.dumps(fields) + '\n')
    print(json.dumps(fields), flush=True)


def token_seconds():
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(raw)['claudeAiOauth']['expiresAt'] / 1000 - time.time()


rows = [line.split() for line in (R / 'cells.tsv').read_text().splitlines() if line.strip()]
for name, task, arm, config, _rep in rows:
    verdict_path = OUT / f'verdict-{name}.json'
    if verdict_path.is_file():
        if json.loads(verdict_path.read_text())['status'] == 'STOP':
            log(event='pause', reason='STOP verdict present', cell=name)
            sys.exit(2)
        continue
    while True:
        if token_seconds() < 6300:
            log(event='pause', reason='token under 6300 s', cell=name)
            sys.exit(3)
        rc = subprocess.run([sys.executable, str(R / 'run_cell.py'), str(L / 'runtime.json'), name, task, arm,
                             config]).returncode
        log(event='run', cell=name, rc=rc)
        if rc != 3:
            break
        time.sleep(120)
    if rc == 2:
        log(event='pause', reason='STOP', cell=name)
        sys.exit(2)
    after = json.loads(verdict_path.read_text()).get('claude_limits_after') or {}
    used = (after.get('seven_day') or {}).get('used')
    if used is not None and used >= 97:
        log(event='pause', reason=f'seven-day {used}%', cell=name)
        sys.exit(4)
log(event='complete')
