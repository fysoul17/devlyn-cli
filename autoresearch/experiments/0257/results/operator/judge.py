"""Operator tool (not apparatus) for root's 0257 judgments (decide.py "audited", "severe", "witnesses", ...).
0256's judge.py with runtime path from NX01_0257_RUNTIME and 0257 cells.tsv.

judge.py cells                    measured cells and their tasks
judge.py findings                 every severe assessor finding of the measured cells, as JSON
judge.py probe <cell>...         malformed-JSON probe, writes probes.json in runtime output
judge.py qualify-probe <0256-runtime.json> <cell>...  probe 0256 trees read-only, print results only
judge.py run <witness> <cell>...  run one witness on each cell's snapshot copy in the cell image (no network, no
                                  capabilities); prints {"<cell>": true|false}, true = the defect reproduces.

A witness is a Node (.js) or Python (.py) script run from the snapshot root as /work. It exits 1 when the claimed
defect reproduces on that tree, 0 when the tree behaves correctly, and anything else for a witness failure, which stops
the run.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RUNTIME = Path(os.environ['NX01_0257_RUNTIME'])
CONFIG = json.loads(RUNTIME.read_text())
LIVE = Path(CONFIG['output']).parent
OUT = Path(CONFIG['output'])
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
    image = CONFIG['image']
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


def probe(cells, source_runtime=None):
    witness = Path(__file__).resolve().parents[1] / 'witnesses/f-malformed-json.js'
    runtime = json.loads(Path(source_runtime).read_text()) if source_runtime else CONFIG
    source_out = Path(runtime['output'])
    image = runtime['image']
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = json.loads((OUT / 'probes.json').read_text()) if not source_runtime and (OUT / 'probes.json').is_file() else {}
    schedule_file = CELLS.parent.parent / '0256/cells.tsv' if source_runtime else CELLS
    schedule = {line.split()[0]: line.split()[1] for line in schedule_file.read_text().splitlines() if line}
    for cell in cells:
        task = schedule[cell]
        if task not in ('F10', 'F11'):
            raise ValueError(f'{cell}: probe requires F10 or F11')
        if not (source_out / f'verdict-{cell}.json').is_file():
            raise ValueError(f'{cell}: verdict missing')
        container = f'probe-{cell}'
        temp = tempfile.TemporaryDirectory(prefix='probe-', dir=SCRATCH)
        result = None
        try:
            work = Path(temp.name) / 'work'
            shutil.copytree(source_out / cell / 'snapshot', work, symlinks=True)
            try:
                done = subprocess.run(['docker', 'run', '--rm', '--name', container, '--network', 'none',
                                       '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '501:501',
                                       '--mount', f'type=bind,src={work},dst=/work',
                                       '--mount', f'type=bind,src={witness.parent},dst=/witness,readonly',
                                       '-w', '/work', '-e', 'HOME=/tmp', image, 'node',
                                       f'/witness/{witness.name}', task], capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired as exc:
                error = str(exc)
                try:
                    subprocess.run(['docker', 'rm', '-f', container], capture_output=True, text=True,
                                   check=True, timeout=10)
                except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as cleanup:
                    error += f'; container cleanup failed: {cleanup}'
                result = {'class': 'unassessable', 'store_preserved': None, 'error': error}
            else:
                if done.returncode:
                    result = {'class': 'unassessable', 'store_preserved': None, 'error': done.stderr[-800:]}
                else:
                    try:
                        result = json.loads(done.stdout.strip().splitlines()[-1])
                        if result.get('class') not in ('json_error_400', 'html_400', 'other', 'unassessable'):
                            raise ValueError('invalid probe class')
                    except (IndexError, ValueError) as exc:
                        result = {'class': 'unassessable', 'store_preserved': None, 'error': str(exc)}
        finally:
            try:
                temp.cleanup()
            except OSError as exc:
                if result is None:
                    raise
                result['error'] = f'{result.get("error", "")}; directory cleanup failed: {exc}'.lstrip('; ')
        results[cell] = result
        if not source_runtime:
            (OUT / 'probes.json').write_text(json.dumps(results, indent=2) + '\n')
    return {cell: results[cell] for cell in cells}


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'cells':
        print(json.dumps({name: task for name, task, _ in measured()}, indent=1))
    elif command == 'findings':
        print(json.dumps(findings(), indent=1))
    elif command == 'probe':
        print(json.dumps(probe(sys.argv[2:])))
    elif command == 'qualify-probe':
        print(json.dumps(probe(sys.argv[3:], sys.argv[2])))
    elif command == 'run':
        print(json.dumps(run(sys.argv[2], sys.argv[3:])))
    else:
        raise SystemExit(__doc__)
