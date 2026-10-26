"""Operator tool (not apparatus) for root's 0259 judgments.
0257's judge.py with runtime path from NX01_0259_RUNTIME and 0259 cells.tsv.
NX01_0259_JUDGE_SCRATCH selects an absolute scratch directory when set.

judge.py cells                    measured cells and their tasks
judge.py findings                 every severe assessor finding of the measured cells, as JSON
judge.py probe <cell>...         malformed-JSON probe, writes probes.json in runtime output
judge.py qualify-probe <0256-runtime.json> <cell>...  probe 0256 trees read-only, print results only
judge.py run <witness> <cell>...  run twice on each snapshot; writes witnesses.json.

A witness is a Node (.js) or Python (.py) script run from the snapshot root as /work. It exits 1 when the claimed
defect reproduces on that tree, 0 when the tree behaves correctly, and 2 for an unresolved witness.
"""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RUNTIME = Path(os.environ['NX01_0259_RUNTIME'])
CONFIG = json.loads(RUNTIME.read_text())
LIVE = Path(CONFIG['output']).parent
OUT = Path(CONFIG['output'])
scratch_override = os.environ.get('NX01_0259_JUDGE_SCRATCH')
SCRATCH = Path(scratch_override) if scratch_override else LIVE / 'scratch' / 'judge'
if scratch_override and not SCRATCH.is_absolute():
    raise ValueError('NX01_0259_JUDGE_SCRATCH must be an absolute path')
CELLS = Path(__file__).resolve().parents[2] / 'cells.tsv'


def stage_witness(witness, temp):
    witness_dir = Path(temp) / 'witness'
    witness_dir.mkdir()
    copied = witness_dir / witness.name
    shutil.copy2(witness, copied)
    if hashlib.sha256(copied.read_bytes()).digest() != hashlib.sha256(witness.read_bytes()).digest():
        raise ValueError(f'witness copy differs from source: {witness}')
    return witness_dir


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
    if witness.stem == 'd3-parseoptions-override':
        seal = json.loads((LIVE / 'instructions.seal.json').read_text())
        if hashlib.sha256(witness.read_bytes()).hexdigest() != seal['witness_sha256']:
            raise ValueError('D3 witness differs from pre-SMOKE seal')
    image = CONFIG['image']
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = OUT / 'witnesses.json'
    result = json.loads(path.read_text()) if path.is_file() else {}
    label = witness.stem
    result.setdefault(label, {})
    for cell in cells:
        attempts = []
        for index in range(2):
            with tempfile.TemporaryDirectory(prefix='witness-', dir=SCRATCH) as temp:
                work = Path(temp) / 'work'
                shutil.copytree(OUT / cell / 'snapshot', work, symlinks=True)
                witness_dir = stage_witness(witness, temp)
                container = f'witness-{cell}-{index}'
                try:
                    done = subprocess.run(['docker', 'run', '--rm', '--name', container, '--network', 'none', '--cap-drop', 'ALL',
                                           '--security-opt', 'no-new-privileges', '--user', '501:501',
                                           '--mount', f'type=bind,src={work},dst=/work',
                                           '--mount', f'type=bind,src={witness_dir},dst=/witness,readonly',
                                           '-w', '/work', '-e', 'HOME=/tmp', image,
                                           'python3' if witness.suffix == '.py' else 'node',
                                           f'/witness/{witness.name}'],
                                          capture_output=True, text=True,
                                          timeout=10 if label == 'd3-parseoptions-override' else 30)
                    valid = done.returncode in (0, 1)
                    if label == 'd3-parseoptions-override':
                        marker = {0: 'P0258-WITNESS public', 1: 'P0258-WITNESS bypass'}.get(done.returncode)
                        valid = valid and not done.stderr and done.stdout.splitlines()[-1:] == [marker]
                    exit_code = done.returncode if valid else 2
                    attempts.append({'exit': exit_code, 'error': done.stdout + done.stderr
                                     if exit_code == 2 else None})
                except subprocess.TimeoutExpired as exc:
                    error = str(exc)
                    for captured in (exc.stdout, exc.stderr):
                        if captured:
                            error += '\n' + (captured.decode(errors='replace') if isinstance(captured, bytes) else captured)
                    try:
                        subprocess.run(['docker', 'rm', '-f', container], capture_output=True, text=True,
                                       check=True, timeout=10)
                    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as cleanup:
                        error += f'; container cleanup failed: {cleanup}'
                    attempts.append({'exit': 2, 'error': error})
        exits = [item['exit'] for item in attempts]
        result[label][cell] = {'attempts': attempts, 'result':
                               exits[0] == 1 if exits[0] == exits[1] and exits[0] in (0, 1) else 'unresolved'}
        path.write_text(json.dumps(result, indent=2) + '\n')
    return {cell: result[label][cell] for cell in cells}


def probe(cells, source_runtime=None):
    witness = Path(__file__).resolve().parents[1] / 'witnesses/f-malformed-json.js'
    runtime = json.loads(Path(source_runtime).read_text()) if source_runtime else CONFIG
    source_out = Path(runtime['output'])
    image = runtime['image']
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = json.loads((OUT / 'probes.json').read_text()) if not source_runtime and (OUT / 'probes.json').is_file() else {}
    schedule_file = CELLS.parent.parent / '0256/cells.tsv' if source_runtime else CELLS
    schedule = {line.split()[0]: line.split()[1] for line in schedule_file.read_text().splitlines() if line}
    def once(cell, task):
        container = f'probe-{cell}'
        temp = tempfile.TemporaryDirectory(prefix='probe-', dir=SCRATCH)
        result = None
        try:
            work = Path(temp.name) / 'work'
            shutil.copytree(source_out / cell / 'snapshot', work, symlinks=True)
            witness_dir = stage_witness(witness, temp.name)
            try:
                done = subprocess.run(['docker', 'run', '--rm', '--name', container, '--network', 'none',
                                       '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '501:501',
                                       '--mount', f'type=bind,src={work},dst=/work',
                                       '--mount', f'type=bind,src={witness_dir},dst=/witness,readonly',
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
                        if not isinstance(result, dict):
                            raise ValueError('probe result is not an object')
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
        return result

    for cell in cells:
        task = schedule[cell]
        if task not in ('F10', 'F11'):
            raise ValueError(f'{cell}: probe requires F10 or F11')
        if not (source_out / f'verdict-{cell}.json').is_file():
            raise ValueError(f'{cell}: verdict missing')
        previous = results.get(cell)
        attempts = list(previous.get('attempts', [previous])) if isinstance(previous, dict) else []
        if not attempts:
            attempts.append(once(cell, task))
        if attempts[-1]['class'] == 'unassessable' and len(attempts) < 2:
            attempts.append(once(cell, task))
        results[cell] = dict(attempts=attempts, **attempts[-1])
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
