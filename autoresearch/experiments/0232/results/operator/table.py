"""Operator tool (not apparatus): table.py — the per-cell table for the 0232 stage-1 RESULT, from the verdicts.

Columns: cell, task, arm, config, replicate, status (product verdict), owner wall s, input, output, usage completeness,
public checks, oracle rows passed/total, scope violations, methodology (I: compliance; F: obligations), account.
"""
import json
from pathlib import Path

LIVE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (Path.home() / '.local/share/nx01/0232-apparatus/autoresearch/experiments/0232/cells.tsv')
         .read_text().splitlines() if line and not line.startswith('#')]
def public(name):
    checks = LIVE / 'out' / name / 'checks.json'
    return ('pass' if json.loads(checks.read_text())['public_pass'] else 'fail') if checks.exists() else '?'


FIRST_ACCOUNT = {'m01', 'm02', 'm03', 'm04', 'm05', 'm06', 'm07', 'm08', 'm09', 'm10'}

print('| cell | task | arm | config | rep | status | wall s | input | output | usage | public | oracle | scope | methodology | account |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for name, task, arm, config, replicate in CELLS:
    path = LIVE / 'out' / f'verdict-{name}.json'
    if not path.exists():
        print(f'| {name} | {task} | {arm} | {config} | {replicate} | (no verdict) |' + ' |' * 9)
        continue
    v = json.loads(path.read_text())
    oracle = v.get('oracle') or []
    passed = sum(r['status'] == 'PASS' for r in oracle)
    method = ('compliant' if (v.get('compliance') or {}).get('compliant') else 'not compliant: ' + ', '.join((v.get('compliance') or {}).get('reasons') or [])) if arm == 'I' else \
             ('obligations ' + ('met' if (v.get('obligations') or {}).get('satisfied') else 'unmet (nonbinding)')) if arm == 'F' else '—'
    wall = 5400 if v.get('owner_status') == 'HANG_TIMEOUT' else round(v.get('owner_seconds') or 0)
    print(f"| {name} | {task} | {arm} | {config} | {replicate} | {v['status']} | {wall} | {v.get('input_tokens')} | "
          f"{v.get('output_tokens')} | {v.get('usage')} | {public(name)} | "
          f"{passed}/{len(oracle)} | {len(v.get('scope_violations') or [])} | {method} | {'1' if name[:3] in FIRST_ACCOUNT else '2'} |")
