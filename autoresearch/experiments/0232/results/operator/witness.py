"""Operator tool (not apparatus) for root's severe-finding dispositions (0232 §6, decide.py "severe"/"witnesses").

witness.py findings                        list every severe assessor finding of the measured cells as JSON
witness.py run <witness.js> <cell>...      run one witness on each cell's snapshot copy in the cell image (no network,
                                           no capabilities); prints {"<cell>": true|false}, true = the defect reproduces.

A witness is a Node script (.js) or a Python script (.py) run from the snapshot root as /work. It exits 1 when the claimed defect reproduces on that
tree, 0 when the tree behaves correctly, and anything else for a witness failure, which stops the run.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

LIVE = Path(__file__).resolve().parent
OUT = LIVE / 'out'
IMAGE = json.loads((LIVE / 'runtime.json').read_text())['image']


def findings():
    rows = []
    for path in sorted(OUT.glob('verdict-m*.json')):
        if '.stop-' in path.name:
            continue
        verdict = json.loads(path.read_text())
        for assessment in verdict.get('assessments') or []:
            for index, finding in enumerate(assessment.get('severe_findings') or []):
                rows.append(dict(cell=verdict['cell'], key=f'{assessment["route"]["engine"]}:{index}', finding=finding))
    return rows


def run(witness, cells):
    witness = Path(witness).resolve()
    result = {}
    for cell in cells:
        with tempfile.TemporaryDirectory(prefix='witness-', dir=LIVE / 'scratch') as temp:
            work = Path(temp) / 'work'
            shutil.copytree(OUT / cell / 'snapshot', work, symlinks=True)
            done = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL', '--security-opt',
                                   'no-new-privileges', '--user', '501:501', '--mount', f'type=bind,src={work},dst=/work',
                                   '--mount', f'type=bind,src={witness.parent},dst=/witness,readonly', '-w', '/work',
                                   '-e', 'HOME=/tmp', IMAGE, 'python3' if witness.suffix == '.py' else 'node', f'/witness/{witness.name}'],
                                  capture_output=True, text=True, timeout=300)
        if done.returncode not in (0, 1):
            raise SystemExit(f'{cell}: witness failed (exit {done.returncode}): {(done.stdout + done.stderr)[-800:]}')
        result[cell] = done.returncode == 1
    return result


if __name__ == '__main__':
    if sys.argv[1] == 'findings':
        print(json.dumps(findings(), indent=1, ensure_ascii=False))
    elif sys.argv[1] == 'run':
        print(json.dumps(run(sys.argv[2], sys.argv[3:])))
