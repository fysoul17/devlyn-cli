"""Operator tool (not apparatus) for the 0265 witnesses and probe, run after the last cell with no cell running.
0261's judge.py (the hardened docker_attempt form) with runtime path from NX01_0265_RUNTIME, 0265 cells.tsv and the
frozen witness list below: a witness whose bytes differ from its pin is refused.
NX01_0265_JUDGE_SCRATCH selects an absolute scratch directory under /private/tmp when set.

judge.py cells                    measured cells and their tasks
judge.py findings                 every severe assessor finding of the measured cells, as JSON
judge.py probe <cell>...          malformed-JSON probe, writes probes.json in runtime output
judge.py probe-all                the probe on every F10 and F11 graded tree
judge.py run <witness> <cell>...  run twice on each snapshot (a cell or an archived attempt <cell>.stop-N); writes
                                  witnesses.json
judge.py run-all                  every witness of D3, D4 and F10 on every final and archived graded tree of its task,
                                  twice, serially; a pair already in witnesses.json is skipped
judge.py qualify <witness> <tree>...       two passes on copies of control trees (DESIGN Q5); prints, writes nothing
judge.py qualify-probe <task> <tree>...    the probe on copies of control trees; prints, writes nothing

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

RUNTIME = Path(os.environ['NX01_0265_RUNTIME'])
CONFIG = json.loads(RUNTIME.read_text())
LIVE = Path(CONFIG['output']).parent
OUT = Path(CONFIG['output'])
scratch_override = os.environ.get('NX01_0265_JUDGE_SCRATCH')
SCRATCH = Path(scratch_override) if scratch_override else LIVE / 'scratch' / 'judge'
if scratch_override and (not SCRATCH.is_absolute() or not SCRATCH.resolve().is_relative_to('/private/tmp')):
    raise ValueError('NX01_0265_JUDGE_SCRATCH must be an absolute path under /private/tmp')
CELLS = Path(__file__).resolve().parents[2] / 'cells.tsv'
WITNESS_DIR = Path(__file__).resolve().parents[1] / 'witnesses'
# Frozen witness list (DESIGN "Grading"): stem -> (task, sha256 of the bytes copied from its source experiment).
WITNESSES = {
    'd4-writer-death': ('D4', '5c0df523f0a556a6a6ff2c94a02f99ad9dc8993387e7605d04a77b101ea34fdc'),
    'd4-writer-stall': ('D4', '65ec911916b025214442f398a0ee89060de25d143c20721e0e0c808fce5b2f33'),
    'd4-writer-startup': ('D4', 'a57350d0629a4e3fd5dd082d419cba9792c51a5fe625fd54e1935c09a0ffba26'),
    'f10-one-process-two-apps': ('F10', 'e5bb4f755383923bf12ffe79b8aa6d6c5f9f18efbd61bdc8bfd29cfb3dda0e26'),
    'f10-one-process-path-alias': ('F10', '707bc1ef27589934573bb0295986eab1348a92f2ca1faf5286bc5d8e76fdac58'),
    'f10-nonobject-items-file': ('F10', 'b8d014e14f91a994130f0d467e3fd2786cb5361a1275b82dc01555b7d407f36c'),
    'd3-executable-delimiter': ('D3', 'f10c6cf91fb2cd3ded81a37e4ee38955eb7ac1d479ce21345a9167e17619d475'),
    'd3-regression-child-probe': ('D3', '94d7079d7f3268538c526df0df8636521b9c09f07c362a2d26b5b3ba7be37346'),
    'd3-parseoptions-override': ('D3', '5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61'),
}
HARM = tuple(stem for stem in WITNESSES if stem != 'd3-parseoptions-override')  # parseOptions is a behaviour count
PROBE = ('f-malformed-json.js', '6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb')
# The witnesses' own timers need their source experiments' limits: d3-regression-child-probe allows its test 18 s
# (0257's judge gave every witness 300 s) and d3-parseoptions-override exits at 10 s (0259's judge used 10 s).
LIMITS = {'d3-regression-child-probe': 300, 'd3-parseoptions-override': 10}
MARKERS = {0: 'P0258-WITNESS public', 1: 'P0258-WITNESS bypass'}  # 0259: parseOptions is valid only with its marker


def frozen(witness):
    """The pinned witness file for a stem or path; refuse anything not frozen or whose bytes differ from its pin."""
    stem = Path(witness).stem
    if stem not in WITNESSES:
        raise ValueError(f'{stem}: not a frozen 0265 witness')
    path = Path(witness).resolve() if Path(witness).suffix else next(WITNESS_DIR.glob(stem + '.*')).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != WITNESSES[stem][1]:
        raise ValueError(f'{path}: bytes differ from the frozen sha256 of {stem}')
    return path


def limit(stem):
    return 300 if stem.startswith('d4-') else LIMITS.get(stem, 30)


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


def graded_attempts(name):
    """The slot's final attempt and its archived attempts (<name>.stop-N, each with its own evidence; an assessor
    regrade shares the final's tree) that have a graded tree, and those without."""
    archived = sorted((p.name for p in OUT.glob(f'{name}.stop-*') if p.is_dir()),
                      key=lambda attempt: int(attempt.rsplit('.stop-', 1)[1]))
    attempts = [name, *archived]
    return ([a for a in attempts if (OUT / a / 'snapshot').is_dir()],
            [a for a in attempts if not (OUT / a / 'snapshot').is_dir()])


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


def witness_pass(witness, tree, cell, container):
    """One pass of a witness on a scratch copy of a tree: the attempt record 0261 stored, with stdout kept on exit 1."""
    label = witness.stem
    with tempfile.TemporaryDirectory(prefix='witness-', dir=SCRATCH) as temp:
        work = Path(temp) / 'work'
        shutil.copytree(tree, work, symlinks=True)
        witness_dir = stage_witness(witness, temp)
        done, cleanup_error, invalid_error = docker_attempt(
            cell, container, ['--network', 'none', '--cap-drop', 'ALL',
                              '--security-opt', 'no-new-privileges', '--user', '501:501',
                              '--mount', f'type=bind,src={work},dst=/work',
                              '--mount', f'type=bind,src={witness_dir},dst=/witness,readonly',
                              '-w', '/work', '-e', 'HOME=/tmp', CONFIG['image'],
                              'python3' if witness.suffix == '.py' else 'node',
                              f'/witness/{witness.name}'],
            limit(label))
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
        if label == 'd3-parseoptions-override':
            valid = (done.returncode in MARKERS and not done.stderr
                     and done.stdout.splitlines()[-1:] == [MARKERS[done.returncode]])
        exit_code = done.returncode if valid else 2
        attempt = {'exit': exit_code, 'error': done.stdout + done.stderr if exit_code == 2 else None}
        if exit_code == 1:
            attempt['stdout'] = done.stdout  # the hung test and its stack, for the false-completion packet
    if cleanup_error:
        attempt['cleanup_error'] = cleanup_error
    return attempt


def outcome(attempts):
    exits = [item['exit'] for item in attempts]
    return (('not_applicable' if exits[0] == 3 else exits[0] == 1)
            if len(exits) == 2 and exits[0] == exits[1] and exits[0] in (0, 1, 3) else 'unresolved')


def run(witness, cells):
    witness = frozen(witness)
    witness_sha256 = hashlib.sha256(witness.read_bytes()).hexdigest()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = OUT / 'witnesses.json'
    result = json.loads(path.read_text()) if path.is_file() else {}
    label = witness.stem
    result.setdefault(label, {})
    for cell in cells:
        previous = result[label].get(cell)
        if previous is not None and previous.get('witness_sha256') != witness_sha256:
            raise ValueError(f'{cell}: witness differs from stored witness_sha256; use a new file name')
    for cell in cells:
        previous = result[label].get(cell)
        attempts = list(previous['attempts']) if previous is not None else []
        for index in range(len(attempts), 2):
            attempts.append(witness_pass(witness, OUT / cell / 'snapshot', cell, f'witness-{cell}-{index}'))
            result[label][cell] = {'attempts': attempts, 'result': outcome(attempts), 'witness_sha256': witness_sha256}
            path.write_text(json.dumps(result, indent=2) + '\n')
    return {cell: result[label][cell] for cell in cells}


def run_all():
    """Every witness of a task on every final and archived graded tree of that task; finished pairs are skipped."""
    done, skipped = {}, []
    rows = measured()
    for label, (task, _) in WITNESSES.items():
        trees = []
        for name, cell_task, _ in rows:
            if cell_task == task:
                graded, ungraded = graded_attempts(name)
                trees += graded
                skipped += [f'{label} {attempt}: no graded tree' for attempt in ungraded]
        done[label] = run(label, trees)
    for line in skipped:
        print('skipped: ' + line, file=sys.stderr)
    return {label: {cell: entry['result'] for cell, entry in cells.items()} for label, cells in done.items()}


def probe_once(tree, task, cell, container):
    witness = WITNESS_DIR / PROBE[0]
    if hashlib.sha256(witness.read_bytes()).hexdigest() != PROBE[1]:
        raise ValueError(f'{witness}: bytes differ from the frozen probe sha256')
    temp = tempfile.TemporaryDirectory(prefix='probe-', dir=SCRATCH)
    result = None
    try:
        work = Path(temp.name) / 'work'
        shutil.copytree(tree, work, symlinks=True)
        witness_dir = stage_witness(witness, temp.name)
        done, cleanup_error, invalid_error = docker_attempt(
            cell, container, ['--network', 'none', '--cap-drop', 'ALL',
                              '--security-opt', 'no-new-privileges', '--user', '501:501',
                              '--mount', f'type=bind,src={work},dst=/work',
                              '--mount', f'type=bind,src={witness_dir},dst=/witness,readonly',
                              '-w', '/work', '-e', 'HOME=/tmp', CONFIG['image'], 'node',
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


def probe(cells):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = json.loads((OUT / 'probes.json').read_text()) if (OUT / 'probes.json').is_file() else {}
    schedule = {line.split()[0]: line.split()[1] for line in CELLS.read_text().splitlines() if line}
    for cell in cells:
        task = schedule[cell]
        if task not in ('F10', 'F11'):
            raise ValueError(f'{cell}: probe requires F10 or F11')
        if not (OUT / f'verdict-{cell}.json').is_file():
            raise ValueError(f'{cell}: verdict missing')
        previous = results.get(cell)
        attempts = list(previous.get('attempts', [previous])) if isinstance(previous, dict) else []
        if not attempts:
            attempts.append(probe_once(OUT / cell / 'snapshot', task, cell, f'probe-{cell}'))
            results[cell] = dict(attempts=attempts, **attempts[-1])
            (OUT / 'probes.json').write_text(json.dumps(results, indent=2) + '\n')
        if attempts[-1]['class'] == 'unassessable' and len(attempts) < 2:
            attempts.append(probe_once(OUT / cell / 'snapshot', task, cell, f'probe-{cell}'))
            results[cell] = dict(attempts=attempts, **attempts[-1])
            (OUT / 'probes.json').write_text(json.dumps(results, indent=2) + '\n')
    return {cell: results[cell] for cell in cells}


def probe_all():
    """The probe on every F10 and F11 final graded tree of both configs (R2 reads the final attempt's class)."""
    cells = [name for name, task, _ in measured() if task in ('F10', 'F11')]
    for name in cells:
        if not (OUT / name / 'snapshot').is_dir():
            print(f'skipped: probe {name}: no graded tree', file=sys.stderr)
    return {cell: entry['class'] for cell, entry in probe([c for c in cells if (OUT / c / 'snapshot').is_dir()]).items()}


def qualify(witness, trees):
    """DESIGN Q5 controls: two passes on scratch copies of trees outside the output folder; nothing is written."""
    witness = frozen(witness)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = {}
    for index, tree in enumerate(trees):
        attempts = [witness_pass(witness, Path(tree), str(tree), f'witness-qualify-{os.getpid()}-{index}-{n}')
                    for n in range(2)]
        results[str(tree)] = {'attempts': attempts, 'result': outcome(attempts)}
    return results


def qualify_probe(task, trees):
    if task not in ('F10', 'F11'):
        raise ValueError('probe requires F10 or F11')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = {}
    for index, tree in enumerate(trees):
        attempts = [probe_once(Path(tree), task, str(tree), f'probe-qualify-{os.getpid()}-{index}-0')]
        if attempts[-1]['class'] == 'unassessable':
            attempts.append(probe_once(Path(tree), task, str(tree), f'probe-qualify-{os.getpid()}-{index}-1'))
        results[str(tree)] = dict(attempts=attempts, **attempts[-1])
    return results


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'cells':
        print(json.dumps({name: task for name, task, _ in measured()}, indent=1))
    elif command == 'findings':
        print(json.dumps(findings(), indent=1))
    elif command == 'probe':
        print(json.dumps(probe(sys.argv[2:])))
    elif command == 'probe-all':
        print(json.dumps(probe_all(), indent=1))
    elif command == 'run':
        print(json.dumps(run(sys.argv[2], sys.argv[3:])))
    elif command == 'run-all':
        print(json.dumps(run_all(), indent=1))
    elif command == 'qualify':
        print(json.dumps(qualify(sys.argv[2], sys.argv[3:]), indent=1))
    elif command == 'qualify-probe':
        print(json.dumps(qualify_probe(sys.argv[2], sys.argv[3:]), indent=1))
    else:
        raise SystemExit(__doc__)
