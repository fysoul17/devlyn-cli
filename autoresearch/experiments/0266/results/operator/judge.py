"""Operator tool (not apparatus) for the 0266 witnesses and probe, run after the last cell with no cell running.
0261's judge.py (the hardened docker_attempt form) with runtime path from NX01_0266_RUNTIME, 0266 cells.tsv and the
frozen witness list below: a witness whose bytes differ from its pin is refused.
NX01_0266_JUDGE_SCRATCH selects an absolute scratch directory under /private/tmp when set.

judge.py cells                    measured cells and their tasks
judge.py findings                 every severe assessor finding of the measured cells, as JSON
judge.py probe <cell>...          malformed-JSON probe, writes probes.json in runtime output
judge.py probe-all                the probe on every F10 and F11 graded tree
judge.py run <witness> <cell>...  run twice on each snapshot (a cell or an archived attempt <cell>.stop-N); writes
                                  witnesses.json
judge.py run-all <task>           every witness of one task (D3, D4 or F10) on every final and archived graded tree of
                                  that task, twice, serially; a pair already in witnesses.json is skipped. One process
                                  per task may run at once: witnesses.json and probes.json are updated under an
                                  exclusive lock on <file>.lock and replaced atomically
judge.py controls                 DESIGN Q5: every control of CONTROLS through the same passes as run-all and probe-all,
                                  on trees built in scratch (never in the output folder); writes
                                  <runtime root>/q5-controls.json and prints the table

A witness is a Node (.js) or Python (.py) script run from the snapshot root as /work. It exits 1 when the claimed
defect reproduces on that tree, 0 when the tree behaves correctly, 2 for an unresolved witness, and 3 when its interface is not applicable.
"""
import fcntl
import importlib.util
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RUNTIME = Path(os.environ['NX01_0266_RUNTIME'])
CONFIG = json.loads(RUNTIME.read_text())
LIVE = Path(CONFIG['output']).parent
OUT = Path(CONFIG['output'])
scratch_override = os.environ.get('NX01_0266_JUDGE_SCRATCH')
SCRATCH = Path(scratch_override) if scratch_override else LIVE / 'scratch' / 'judge'
if scratch_override and (not SCRATCH.is_absolute() or not SCRATCH.resolve().is_relative_to('/private/tmp')):
    raise ValueError('NX01_0266_JUDGE_SCRATCH must be an absolute path under /private/tmp')
CELLS = Path(__file__).resolve().parents[2] / 'cells.tsv'
WITNESS_DIR = Path(__file__).resolve().parents[1] / 'witnesses'
PRIOR_WITNESS_DIR = Path(__file__).resolve().parents[3] / '0265/results/witnesses'  # the witnesses 0266 keeps as they are
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
ARCHIVE = Path.home() / '.local/share/nx01/archive'
# DESIGN Q5. (control id, witness stem or 'probe', expected result, tree, plant, note). A tree is ('archive', <cell folder
# under ARCHIVE>), whose snapshot is copied (an F10/F11 snapshot gets the base tree's node_modules, which the archived
# snapshots lack), or ('base', <task>), the task's base tree as prepare.source builds it, without .git. Archived trees
# were chosen by their own run's record with the same witness bytes (0261), by 0257's record (stall: 0256's bytes, which
# differ from 0261's only in reading an injection-free finish as not applicable), or by reading the code (named).
CONTROLS = (
    ('d4-death-reproduces', 'd4-writer-death', True, ('archive', 'reports-0261/d003-D4-claude-C-r2'), None, ''),
    ('d4-death-does-not', 'd4-writer-death', False, ('archive', 'reports-0261/d001-D4-claude-B-r1'), None, ''),
    ('d4-death-not-applicable', 'd4-writer-death', 'not_applicable', ('base', 'D4'), None, ''),
    ('d4-stall-reproduces', 'd4-writer-stall', True, ('archive', 'reports-0256-0260/0257/d230-D4-claude-B-r15'), None,
     'no 0261 tree reproduced stall; 0257 d230 did'),
    ('d4-stall-does-not', 'd4-writer-stall', False, ('archive', 'reports-0261/d001-D4-claude-B-r1'), None, ''),
    ('d4-stall-not-applicable', 'd4-writer-stall', 'not_applicable', ('base', 'D4'), None, ''),
    ('d4-startup-reproduces', 'd4-writer-startup', True, ('archive', 'reports-0261/d003-D4-claude-C-r2'), None, ''),
    ('d4-startup-does-not', 'd4-writer-startup', False, ('archive', 'reports-0261/d001-D4-claude-B-r1'), None, ''),
    ('d4-startup-not-applicable', 'd4-writer-startup', 'not_applicable', ('base', 'D4'), None, ''),
    ('d4-startup-d021', 'd4-writer-startup', True, ('archive', 'reports-0256-0260/0257/d021-D4-claude-B-r2'), None,
     '0257 erratum 1: the first startup witness missed this tree'),
    ('d4-death-no-pytest', 'd4-writer-death', 'unresolved', ('archive', 'reports-0261/d003-D4-claude-C-r2'),
     'no-pytest', ''),
    ('d4-stall-no-pytest', 'd4-writer-stall', 'unresolved', ('archive', 'reports-0261/d003-D4-claude-C-r2'),
     'no-pytest', ''),
    ('d4-startup-no-pytest', 'd4-writer-startup', 'unresolved', ('archive', 'reports-0261/d003-D4-claude-C-r2'),
     'no-pytest', ''),
    ('f10-two-apps-reproduces', 'f10-one-process-two-apps', True, ('archive', 'reports-0261/c004-F10-claude-B-r2'),
     None, ''),
    ('f10-two-apps-does-not', 'f10-one-process-two-apps', False, ('archive', 'reports-0261/c001-F10-claude-B-r1'),
     None, ''),
    ('f10-two-apps-not-applicable', 'f10-one-process-two-apps', 'not_applicable', ('base', 'F10'), None,
     'the base exports app only, no createApp'),
    ('f10-path-alias-reproduces', 'f10-one-process-path-alias', True, ('archive', 'reports-0261/c004-F10-claude-B-r2'),
     None, ''),
    ('f10-path-alias-does-not', 'f10-one-process-path-alias', False, ('archive', 'reports-0261/c001-F10-claude-B-r1'),
     None, ''),
    ('f10-path-alias-not-applicable', 'f10-one-process-path-alias', 'not_applicable', ('base', 'F10'), None,
     'the base exports app only, no createApp'),
    ('f10-nonobject-reproduces', 'f10-nonobject-items-file', True, ('archive', 'reports-0261/c001-F10-claude-B-r1'),
     None, ''),
    ('f10-nonobject-does-not', 'f10-nonobject-items-file', False, ('archive', 'reports-0256-0260/0257/c004-F10-codex-B-r1'),
     None, 'no archived run recorded this witness passing; chosen by reading the code: express.json({strict: false}) '
     'and `req.body || {}` give every non-object body 400 invalid_body name'),
    ('f10-nonobject-not-applicable', 'f10-nonobject-items-file', 'not_applicable', ('base', 'F10'), 'no-exports', ''),
    ('d3-delimiter-reproduces', 'd3-executable-delimiter', True, ('archive', 'reports-0256-0260/0257/d051-D3-codex-B-r4'),
     None, ''),
    ('d3-delimiter-does-not', 'd3-executable-delimiter', False, ('archive', 'reports-0256-0260/0257/d001-D3-claude-A-r1'),
     None, ''),
    ('d3-delimiter-no-interface', 'd3-executable-delimiter', True, ('base', 'D3'), 'no-index',
     'DESIGN Q5 (O14): the frozen script has no not-applicable reading; it counts the missing module as the defect'),
    ('d3-child-probe-reproduces', 'd3-regression-child-probe', True,
     ('archive', 'reports-0256-0260/0257/d051-D3-codex-B-r4'), None, ''),
    ('d3-child-probe-does-not', 'd3-regression-child-probe', False, ('base', 'D3'), 'child-test-from-file',
     'only d051 holds a test of that name, and it reproduces'),
    ('d3-child-probe-no-interface', 'd3-regression-child-probe', False, ('base', 'D3'), None,
     'the frozen script reads an absent test as exit 0 ("correct/not applicable"), never 3'),
    ('probe-json-error-400', 'probe', 'json_error_400', ('archive', 'reports-0256-0260/0257/c001-F10-claude-A-r1'),
     None, "0257's recorded class"),
    ('probe-html-400', 'probe', 'html_400', ('archive', 'reports-0256-0260/0257/c002-F10-claude-B-r1'), None,
     "0257's recorded class"),
)
CHILD_TEST = 'reports-0256-0260/0257/d051-D3-codex-B-r4/snapshot/tests'


def frozen(witness):
    """The pinned witness file for a stem or path; refuse anything not frozen or whose bytes differ from its pin."""
    stem = Path(witness).stem
    if stem not in WITNESSES:
        raise ValueError(f'{stem}: not a frozen 0266 witness')
    path = Path(witness).resolve() if Path(witness).suffix else next(
        path for folder in (WITNESS_DIR, PRIOR_WITNESS_DIR) for path in sorted(folder.glob(stem + '.*'))).resolve()
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


def read(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def update(path, change):
    """One read-modify-write of a shared result file: under an exclusive lock on its sibling <name>.lock it is read
    again, changed and replaced atomically, so run-all processes of different tasks never lose each other's entries."""
    with open(path.with_name(path.name + '.lock'), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = read(path)
        change(result)
        temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        os.replace(temporary, path)
    return result


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


def two_passes(witness, tree, name, attempts, record):
    """A witness's two passes on one tree, as run-all makes them; each new pass is handed to record() as it ends."""
    attempts = list(attempts)
    for index in range(len(attempts), 2):
        attempts.append(witness_pass(witness, tree, name, f'witness-{name}-{index}'))
        record(attempts)
    return {'attempts': attempts, 'result': outcome(attempts)}


def run(witness, cells):
    witness = frozen(witness)
    witness_sha256 = hashlib.sha256(witness.read_bytes()).hexdigest()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = OUT / 'witnesses.json'
    label = witness.stem
    stored = read(path).get(label, {})
    for cell in cells:
        previous = stored.get(cell)
        if previous is not None and previous.get('witness_sha256') != witness_sha256:
            raise ValueError(f'{cell}: witness differs from stored witness_sha256; use a new file name')
    done = {}
    for cell in cells:
        def record(attempts, cell=cell):
            entry = {'attempts': attempts, 'result': outcome(attempts), 'witness_sha256': witness_sha256}
            update(path, lambda result: result.setdefault(label, {}).update({cell: entry}))
        previous = stored.get(cell)
        done[cell] = dict(two_passes(witness, OUT / cell / 'snapshot', cell, previous['attempts'] if previous else [],
                                     record), witness_sha256=witness_sha256)
    return done


def run_all(task):
    """Every witness of one task on every final and archived graded tree of that task; finished pairs are skipped."""
    if task not in {t for t, _ in WITNESSES.values()}:
        raise SystemExit(f'run-all takes a witness task: {sorted({t for t, _ in WITNESSES.values()})}')
    done, skipped = {}, []
    rows = measured()
    for label, (witness_task, _) in WITNESSES.items():
        if witness_task != task:
            continue
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


def probe_attempts(tree, task, name, attempts, record):
    """The probe on one tree, as probe-all makes it: one attempt, and one retry while it is unassessable; each new
    attempt is handed to record() as it ends."""
    attempts = list(attempts)
    while not attempts or (attempts[-1]['class'] == 'unassessable' and len(attempts) < 2):
        attempts.append(probe_once(tree, task, name, f'probe-{name}'))
        record(attempts)
    return dict(attempts=attempts, **attempts[-1])


def probe(cells):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = OUT / 'probes.json'
    stored = read(path)
    schedule = {line.split()[0]: line.split()[1] for line in CELLS.read_text().splitlines() if line}
    done = {}
    for cell in cells:
        task = schedule[cell]
        if task not in ('F10', 'F11'):
            raise ValueError(f'{cell}: probe requires F10 or F11')
        if not (OUT / f'verdict-{cell}.json').is_file():
            raise ValueError(f'{cell}: verdict missing')
        previous = stored.get(cell)

        def record(attempts, cell=cell):
            update(path, lambda result: result.update({cell: dict(attempts=attempts, **attempts[-1])}))
        done[cell] = probe_attempts(OUT / cell / 'snapshot', task, cell,
                                    list(previous.get('attempts', [previous])) if isinstance(previous, dict) else [],
                                    record)
    return done


def probe_all():
    """The probe on every F10 and F11 final graded tree of both configs (R2 reads the final attempt's class)."""
    cells = [name for name, task, _ in measured() if task in ('F10', 'F11')]
    for name in cells:
        if not (OUT / name / 'snapshot').is_dir():
            print(f'skipped: probe {name}: no graded tree', file=sys.stderr)
    return {cell: entry['class'] for cell, entry in probe([c for c in cells if (OUT / c / 'snapshot').is_dir()]).items()}


PLANTS = {
    'no-pytest': 'a pytest.py at the tree root that raises "No module named pytest", so the tests cannot import pytest',
    'no-exports': 'server/index.js exports neither app nor createApp',
    'no-index': 'index.js removed',
    'child-test-from-file': "0257 d051's tests/command.executableSubcommand.test.js and tests/fixtures/pm-literal.js, "
                            'its parent program started from a file instead of node --eval',
}


def plant(kind, tree):
    def replace(path, old, new):
        text = path.read_text()
        if text.count(old) != 1:
            raise ValueError(f'{kind}: {path.name} no longer holds the planted text once')
        path.write_text(text.replace(old, new))
    if kind == 'no-pytest':
        (tree / 'pytest.py').write_text("raise ModuleNotFoundError('No module named pytest')\n")
    elif kind == 'no-exports':
        replace(tree / 'server/index.js', 'module.exports = { app };', 'module.exports = {};')
    elif kind == 'no-index':
        (tree / 'index.js').unlink()
    elif kind == 'child-test-from-file':
        source, test = ARCHIVE / CHILD_TEST, tree / 'tests/command.executableSubcommand.test.js'
        shutil.copy2(source / 'fixtures/pm-literal.js', tree / 'tests/fixtures/pm-literal.js')
        shutil.copy2(source / test.name, test)
        replace(test, "    [\n      '--input-type=module',\n      '--eval',\n      `", '    [\n      parentFile(`')
        replace(test, "      `,\n    ],\n    { encoding: 'utf8', timeout: 10000 },",
                "      `),\n    ],\n    { encoding: 'utf8', timeout: 10000 },")
        replace(test, "import path from 'node:path';\n",
                "import path from 'node:path';\nimport fs from 'node:fs';\nimport os from 'node:os';\n\n"
                'function parentFile(code) {\n'
                "  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'parent-')), 'parent.mjs');\n"
                '  fs.writeFileSync(file, code);\n  return file;\n}\n')
    else:
        raise ValueError(f'unknown plant {kind}')


def control_trees(temp):
    """Each control's tree, built under temp: base trees once per task (prepare.source, .git removed), archived
    snapshots copied, an F10/F11 snapshot without node_modules given its base tree's."""
    spec = importlib.util.spec_from_file_location('prepare0266j', Path(__file__).resolve().parents[2] / 'prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    bases = {}

    def base(task):
        if task not in bases:
            work = temp / f'base-{task}'
            prepare.source(next(t for t in prepare.TASKS['tasks'] if t['id'] == task), CONFIG, work, prepare.base)
            shutil.rmtree(work / '.git')
            bases[task] = work
        return bases[task]
    trees = {}
    for control, _, _, (kind, value), planted, _ in CONTROLS:
        tree = temp / control
        if kind == 'base':
            shutil.copytree(base(value), tree, symlinks=True)
        else:
            shutil.copytree(ARCHIVE / value / 'snapshot', tree, symlinks=True)
            task = Path(value).name.split('-')[1]
            if task in ('F10', 'F11') and not (tree / 'node_modules').exists():
                shutil.copytree(base(task) / 'node_modules', tree / 'node_modules', symlinks=True)
        if planted:
            plant(planted, tree)
        trees[control] = tree
    return trees


def controls():
    """DESIGN Q5: each control through the passes run-all and probe-all make, on scratch trees; the probe twice."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = LIVE / 'q5-controls.json'
    result = dict(schema=1, image=CONFIG['image'], witness_sha256={stem: pin for stem, (_, pin) in WITNESSES.items()},
                  probe_sha256=PROBE[1], controls=[])
    with tempfile.TemporaryDirectory(prefix='q5-controls-', dir=SCRATCH) as temp:
        trees = control_trees(Path(temp))
        for control, check, expected, (kind, value), planted, note in CONTROLS:
            name = 'q5-' + control
            if check == 'probe':
                runs = [probe_attempts(trees[control], Path(value).name.split('-')[1], name, [], lambda _: None)
                        for _ in range(2)]
                found, attempts = [run['class'] for run in runs], [run['attempts'] for run in runs]
                ok = found == [expected] * 2
            else:
                done = two_passes(frozen(check), trees[control], name, [], lambda _: None)
                found, attempts = done['result'], done['attempts']
                ok = found == expected
            result['controls'].append(dict(id=control, check=check, tree=f'{kind} {value}', planted=PLANTS.get(planted),
                                           note=note, expected=expected, result=found, ok=ok, attempts=attempts))
            path.write_text(json.dumps(result, indent=2) + '\n')
    result['result'] = 'PASS' if all(c['ok'] for c in result['controls']) else 'FAIL'
    path.write_text(json.dumps(result, indent=2) + '\n')
    return result


def control_table(result):
    shown = lambda value: str(value).lower() if isinstance(value, bool) else '/'.join(value) if isinstance(
        value, list) else str(value)
    lines = ['control\tcheck\ttree\texpected\tresult\tok']
    lines += [f'{c["id"]}\t{c["check"]}\t{c["tree"]}{" + planted" if c["planted"] else ""}\t{shown(c["expected"])}'
              f'\t{shown(c["result"])}\t{"ok" if c["ok"] else "MISS"}' for c in result['controls']]
    return '\n'.join(lines + [result['result']])


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
    elif command == 'run-all' and len(sys.argv) == 3:
        print(json.dumps(run_all(sys.argv[2]), indent=1))
    elif command == 'controls':
        print(control_table(controls()))
    else:
        raise SystemExit(__doc__)
