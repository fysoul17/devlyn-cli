"""Operator tool (not apparatus) for root's 0256 judgments (decide.py "audited", "severe", "witnesses", ...).
0235's judge.py with 0256's paths: verdicts and snapshots under 0256-live/output, cells from 0256's cells.tsv.

judge.py cells                    measured cells and their tasks
judge.py findings                 every severe assessor finding of the measured cells, as JSON
judge.py run <witness> <cell>...  run one witness on each cell's snapshot copy in the cell image (no network, no
                                  capabilities); prints {"<cell>": true|false}, true = the defect reproduces.

A witness is a Node (.js) or Python (.py) script run from the snapshot root as /work. It exits 1 when the claimed
defect reproduces on that tree, 0 when the tree behaves correctly, and anything else for a witness failure, which stops
the run.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

LIVE = Path.home() / '.local/share/nx01/0256-live'
OUT = LIVE / 'output'
SCRATCH = LIVE / 'scratch' / 'judge'
CELLS = Path(__file__).resolve().parents[2] / 'cells.tsv'


def measured():
    rows = []
    for line in CELLS.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, task = line.split()[:2]
        path = OUT / f'verdict-{name}.json'
        if not path.is_file():
            raise SystemExit(f'{name}: no verdict yet')
        rows.append((name, task, json.loads(path.read_text())))
    return rows


def findings():
    rows = []
    for name, task, verdict in measured():
        for assessment in verdict.get('assessments') or []:
            for index, finding in enumerate(assessment.get('severe_findings') or []):
                rows.append(dict(cell=name, task=task, key=f'{assessment["route"]["engine"]}:{index}', finding=finding))
    return rows


def run(witness, cells):
    witness = Path(witness).resolve()
    image = json.loads((LIVE / 'runtime.json').read_text())['image']
    SCRATCH.mkdir(parents=True, exist_ok=True)
    result = {}
    for cell in cells:
        with tempfile.TemporaryDirectory(prefix='witness-', dir=SCRATCH) as temp:
            work = Path(temp) / 'work'
            shutil.copytree(OUT / cell / 'snapshot', work, symlinks=True)
            done = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL', '--security-opt',
                                   'no-new-privileges', '--user', '501:501', '--mount', f'type=bind,src={work},dst=/work',
                                   '--mount', f'type=bind,src={witness.parent},dst=/witness,readonly', '-w', '/work',
                                   '-e', 'HOME=/tmp', image, 'python3' if witness.suffix == '.py' else 'node',
                                   f'/witness/{witness.name}'],
                                  capture_output=True, text=True, timeout=300)
        if done.returncode not in (0, 1):
            raise SystemExit(f'{cell}: witness failed (exit {done.returncode}): {(done.stdout + done.stderr)[-800:]}')
        result[cell] = done.returncode == 1
    return result


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'cells':
        print(json.dumps({name: task for name, task, _ in measured()}, indent=1))
    elif command == 'findings':
        print(json.dumps(findings(), indent=1))
    elif command == 'run':
        print(json.dumps(run(sys.argv[2], sys.argv[3:])))
    else:
        raise SystemExit(__doc__)
