"""Operator tool (not apparatus) for root's judgments in 0233 and 0234 (decide.py "audited", "severe", "witnesses", ...).

judge.py cells <exp>                          measured cells: dispatched rows of cells.tsv (status not NOT_RUN), with task
judge.py findings <exp>                       every severe assessor finding of the measured cells, as JSON
judge.py run <exp> <witness> <cell>...        run one witness on each cell's snapshot copy in the cell image (no network,
                                              no capabilities); prints {"<cell>": true|false}, true = the defect reproduces.

<exp> is 0233 or 0234. A 0234 cell reused from 0233 ("reused_from") is evaluated on its 0233 snapshot.
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

NX = Path.home() / '.local/share/nx01'
SCRATCH = NX / '0234-live' / 'scratch'


def live(exp):
    return NX / f'{exp}-live'


def measured(exp):
    rows = []
    tsv = NX / f'{exp}-apparatus' / 'autoresearch' / 'experiments' / exp / 'cells.tsv'
    for line in tsv.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, task = line.split()[:2]
        path = live(exp) / 'out' / f'verdict-{name}.json'
        if not path.is_file():
            raise SystemExit(f'{exp} {name}: no verdict yet')
        verdict = json.loads(path.read_text())
        if verdict.get('status') != 'NOT_RUN':
            rows.append((name, task, verdict))
    return rows


def snapshot(exp, name, verdict):
    source = verdict.get('reused_from')
    return (live('0233') / 'out' / source if source else live(exp) / 'out' / name) / 'snapshot'


def findings(exp):
    rows = []
    for name, task, verdict in measured(exp):
        for assessment in verdict.get('assessments') or []:
            for index, finding in enumerate(assessment.get('severe_findings') or []):
                rows.append(dict(cell=name, task=task, key=f'{assessment["route"]["engine"]}:{index}', finding=finding))
    return rows


def run(exp, witness, cells):
    witness = Path(witness).resolve()
    image = json.loads((live(exp) / 'runtime.json').read_text())['image']
    verdicts = {name: verdict for name, _, verdict in measured(exp)}
    SCRATCH.mkdir(exist_ok=True)
    result = {}
    for cell in cells:
        with tempfile.TemporaryDirectory(prefix='witness-', dir=SCRATCH) as temp:
            work = Path(temp) / 'work'
            shutil.copytree(snapshot(exp, cell, verdicts[cell]), work, symlinks=True)
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
    command, exp = sys.argv[1], sys.argv[2]
    if command == 'cells':
        print('\n'.join(f'{name}\t{task}\t{verdict["status"]}' for name, task, verdict in measured(exp)))
    elif command == 'findings':
        print(json.dumps(findings(exp), indent=1, ensure_ascii=False))
    elif command == 'run':
        print(json.dumps(run(exp, sys.argv[3], sys.argv[4:])))
