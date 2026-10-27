"""Operator tool (not apparatus) for root's 0261 judgments.
0257's judge.py with runtime path from NX01_0261_RUNTIME and 0261 cells.tsv.
NX01_0261_JUDGE_SCRATCH selects an absolute scratch directory when set.

judge.py cells                    measured cells and their tasks
judge.py findings                 every severe assessor finding of the measured cells, as JSON
judge.py probe <cell>...         malformed-JSON probe, writes probes.json in runtime output
judge.py qualify-probe <0256-runtime.json> <cell>...  probe 0256 trees read-only, print results only
judge.py run <witness> <cell>...  run twice on each snapshot; writes witnesses.json.

A witness is a Node (.js) or Python (.py) script run from the snapshot root as /work. It exits 1 when the claimed
defect reproduces on that tree, 0 when the tree behaves correctly, 2 for an unresolved witness, and 3 when its interface is not applicable.
"""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RUNTIME = Path(os.environ['NX01_0261_RUNTIME'])
CONFIG = json.loads(RUNTIME.read_text())
LIVE = Path(CONFIG['output']).parent
OUT = Path(CONFIG['output'])
scratch_override = os.environ.get('NX01_0261_JUDGE_SCRATCH')
SCRATCH = Path(scratch_override) if scratch_override else LIVE / 'scratch' / 'judge'
if scratch_override and (not SCRATCH.is_absolute() or not SCRATCH.resolve().is_relative_to('/private/tmp')):
    raise ValueError('NX01_0261_JUDGE_SCRATCH must be an absolute path under /private/tmp')
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


def docker_attempt(cell, container, options, run_limit):
    """Return a started container's result (or timeout); never count failed startup."""
    create_error = None
    state_error = None
    never_started_error = None
    invalid_error = None
    outcome = None
    cleanup_error = None
    try:
        try:
            created = subprocess.run(['docker', 'create', '--name', container, *options],
                                     capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            create_error = str(exc)
        else:
            if created.returncode:
                create_error = f'exit {created.returncode}: {created.stdout}{created.stderr}'
        if create_error is None:
            try:
                outcome = subprocess.run(['docker', 'start', '-a', container], capture_output=True,
                                         text=True, timeout=run_limit)
            except subprocess.TimeoutExpired as exc:
                outcome = exc
            except OSError as exc:
                outcome = subprocess.CompletedProcess(['docker', 'start', '-a', container], 2, '', str(exc))
            try:
                inspected = subprocess.run(['docker', 'inspect', '--format', '{{json .State}}', container],
                                           capture_output=True, text=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired) as exc:
                state_error = str(exc)
            else:
                if inspected.returncode:
                    state_error = f'exit {inspected.returncode}: {inspected.stdout}{inspected.stderr}'
                else:
                    try:
                        state = json.loads(inspected.stdout)
                        if (not isinstance(state, dict)
                                or not isinstance(state.get('StartedAt'), str)
                                or not isinstance(state.get('Running'), bool)
                                or type(state.get('ExitCode')) is not int):
                            raise ValueError('missing or invalid StartedAt, Running, or ExitCode')
                    except (ValueError, TypeError) as exc:
                        state_error = f'{exc}: {inspected.stdout}{inspected.stderr}'
                    else:
                        if state['StartedAt'].startswith('0001-01-01'):
                            output = ''
                            if isinstance(outcome, subprocess.TimeoutExpired):
                                for captured in (outcome.stdout, outcome.stderr):
                                    if captured:
                                        output += captured.decode(errors='replace') if isinstance(captured, bytes) else captured
                            else:
                                output = outcome.stdout + outcome.stderr
                            never_started_error = output
                        elif not isinstance(outcome, subprocess.TimeoutExpired):
                            if state['Running'] or outcome.returncode != state['ExitCode']:
                                invalid_error = (f'docker start exit {outcome.returncode}, '
                                                 f'container ExitCode {state["ExitCode"]}, '
                                                 f'Running {state["Running"]}; stderr: {outcome.stderr}')
                            outcome = subprocess.CompletedProcess(outcome.args, state['ExitCode'],
                                                                  outcome.stdout, outcome.stderr)
    finally:
        try:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True, text=True,
                           check=True, timeout=10)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            cleanup_error = str(exc)
    if create_error is not None:
        detail = f'; container cleanup failed: {cleanup_error}' if cleanup_error else ''
        raise RuntimeError(f'{cell}: docker create failed: {create_error}{detail}')
    if state_error is not None:
        detail = f'; container cleanup failed: {cleanup_error}' if cleanup_error else ''
        raise RuntimeError(f'{cell}: container state unreadable: {state_error}{detail}')
    if never_started_error is not None:
        detail = f'; container cleanup failed: {cleanup_error}' if cleanup_error else ''
        raise RuntimeError(f'{cell}: container never started: {never_started_error}{detail}')
    return outcome, cleanup_error, invalid_error


def run(witness, cells):
    witness = Path(witness).resolve()
    witness_sha256 = hashlib.sha256(witness.read_bytes()).hexdigest()
    image = CONFIG['image']
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = OUT / 'witnesses.json'
    result = json.loads(path.read_text()) if path.is_file() else {}
    label = witness.stem
    result.setdefault(label, {})
    for cell in cells:
        previous = result[label].get(cell)
        if previous is not None and previous.get('witness_sha256') != witness_sha256:
            raise ValueError(f'{cell}: witness differs from stored witness_sha256; use a new file name')
    if witness.name in {p.name for p in (CELLS.parent / 'results/witnesses').glob('*.*')}:
        seal = json.loads((LIVE / 'instructions.seal.json').read_text())
        if witness_sha256 != seal['witness_sha256'].get(witness.name):
            raise ValueError('witness differs from pre-SMOKE seal')
    for cell in cells:
        previous = result[label].get(cell)
        attempts = list(previous['attempts']) if previous is not None else []
        for index in range(len(attempts), 2):
            with tempfile.TemporaryDirectory(prefix='witness-', dir=SCRATCH) as temp:
                work = Path(temp) / 'work'
                shutil.copytree(OUT / cell / 'snapshot', work, symlinks=True)
                witness_dir = stage_witness(witness, temp)
                container = f'witness-{cell}-{index}'
                done, cleanup_error, invalid_error = docker_attempt(
                    cell, container, ['--network', 'none', '--cap-drop', 'ALL',
                                      '--security-opt', 'no-new-privileges', '--user', '501:501',
                                      '--mount', f'type=bind,src={work},dst=/work',
                                      '--mount', f'type=bind,src={witness_dir},dst=/witness,readonly',
                                      '-w', '/work', '-e', 'HOME=/tmp', image,
                                      'python3' if witness.suffix == '.py' else 'node',
                                      f'/witness/{witness.name}'],
                    300 if label.startswith('d4-') else 30)
                if invalid_error:
                    attempt = {'exit': 2, 'error': invalid_error}
                elif isinstance(done, subprocess.TimeoutExpired):
                    error = str(done)
                    for captured in (done.stdout, done.stderr):
                        if captured:
                            error += '\n' + (captured.decode(errors='replace') if isinstance(captured, bytes) else captured)
                    attempt = {'exit': 2, 'error': error}
                else:
                    valid = done.returncode in (0, 1, 3)
                    exit_code = done.returncode if valid else 2
                    attempt = {'exit': exit_code, 'error': done.stdout + done.stderr
                               if exit_code == 2 else None}
                if cleanup_error:
                    attempt['cleanup_error'] = cleanup_error
                attempts.append(attempt)
                exits = [item['exit'] for item in attempts]
                result[label][cell] = {'attempts': attempts, 'result':
                                       ('not_applicable' if exits[0] == 3 else exits[0] == 1)
                                       if len(exits) == 2 and exits[0] == exits[1]
                                       and exits[0] in (0, 1, 3) else 'unresolved',
                                       'witness_sha256': witness_sha256}
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
            done, cleanup_error, invalid_error = docker_attempt(
                cell, container, ['--network', 'none', '--cap-drop', 'ALL',
                                  '--security-opt', 'no-new-privileges', '--user', '501:501',
                                  '--mount', f'type=bind,src={work},dst=/work',
                                  '--mount', f'type=bind,src={witness_dir},dst=/witness,readonly',
                                  '-w', '/work', '-e', 'HOME=/tmp', image, 'node',
                                  f'/witness/{witness.name}', task], 60)
            if invalid_error:
                result = {'class': 'unassessable', 'store_preserved': None, 'error': invalid_error}
            elif isinstance(done, subprocess.TimeoutExpired):
                error = str(done)
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
            if cleanup_error:
                result['cleanup_error'] = cleanup_error
        finally:
            try:
                temp.cleanup()
            except OSError as exc:
                if result is None:
                    raise
                detail = f'directory cleanup failed: {exc}'
                result['cleanup_error'] = f'{result["cleanup_error"]}; {detail}' if 'cleanup_error' in result else detail
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
            results[cell] = dict(attempts=attempts, **attempts[-1])
            if not source_runtime:
                (OUT / 'probes.json').write_text(json.dumps(results, indent=2) + '\n')
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
