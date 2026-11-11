"""DESIGN Q3, Codex config honoured: strict_config_check.py --run-exec <runtime.json> (one model call, the allowed
one; the orchestrator runs it).

The 0265 config.toml (prepare.codex_config, the file both arms get) must load under the pinned Codex's
--strict-config (allowed); the same file plus one unknown top-level key and one unknown [features] key must fail at
config load (violating). Codex 0.164.0 refuses the flag for `codex debug` (DESIGN O1), so both run raw in the cell
image as `codex exec --strict-config`: the credential snapshot is taken as a cell's preflight takes it
(run_cell.snapshot_auth, never printed), and the violating run must exit non-zero naming an unknown key, with no
session event (thread, turn, item) on its stdout and no file in its trace root or sessions folder (no model request),
while the allowed one exits 0. <root>/q3-strict-config.json records the exit codes, the event types and the config
error text (no credential); it is written once, and every strict-config-exec-* config home in scratch is removed.

Exit 0 PASS, 1 FAIL, 3 not run.
"""
import argparse
import functools
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('prepare0265s', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare)
UNKNOWN = ('zz_unknown_top_0265', 'zz_unknown_feature_0265')
PROMPT = 'Reply OK.'
SMOKE_TREE = HERE.parents[2] / 'autoresearch/experiments/0222/smoke/repo'
LABELS = ('allowed', 'violating')
TRACE = '/home/probe/trace'


def configs():
    """(allowed, violating) config.toml texts."""
    allowed = prepare.codex_config(prepare.TASKS['routes']['codex']['owner'])
    if allowed.count('[features]\n') != 1:
        raise ValueError('expected one [features] table')
    return allowed, f'{UNKNOWN[0]} = true\n' + allowed.replace('[features]\n', f'[features]\n{UNKNOWN[1]} = true\n')


def run(argv):
    """(exit code or None on timeout, stdout, stderr) of one docker command."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None, '', 'timed out after 180 s'
    return done.returncode, done.stdout, done.stderr


def exec_home(folder, text, runtime):
    """A config home for one `codex exec` run: the config, the models cache, the login's mount target, a trace root."""
    (folder / '.codex').mkdir(parents=True)
    (folder / '.codex/config.toml').write_text(text)
    if runtime.get('models_cache'):
        shutil.copyfile(runtime['models_cache'], folder / '.codex/models_cache.json')
    (folder / '.codex/auth.json').touch()  # mount target only; the login is bind-mounted read-only
    (folder / 'trace').mkdir()
    return folder


def exec_argv(runtime, home, name):
    """The model-call command, raw in the cell image: the cell's login mount, the 0222 smoke tree, the trace root a
    cell's owner gets."""
    return ['docker', 'run', '--name', name, '--rm', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec',
            '--tmpfs', '/home/probe/.codex/tmp:rw,nosuid,exec,uid=501,gid=501',
            '--mount', f'type=bind,src={home},dst=/home/probe', '--env', 'HOME=/home/probe',
            '--env', 'CODEX_HOME=/home/probe/.codex', '--network', 'bridge',
            '--env', f'CODEX_ROLLOUT_TRACE_ROOT={TRACE}',
            '--mount', f'type=bind,src={Path(runtime["auth"]) / "codex.json"},'
            f'dst=/home/probe/.codex/auth.json,readonly',
            '--mount', f'type=bind,src={SMOKE_TREE},dst=/cell/work,readonly', '-w', '/cell/work',
            runtime['image'], 'timeout', '120s', 'codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check',
            PROMPT]


@functools.cache
def run_cell():
    spec = importlib.util.spec_from_file_location('run_cell0265s', HERE / 'run_cell.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evidence(code, stdout, stderr, home):
    """One exec run as recorded: no credential, only exit code, event types, files written, and the error text."""
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and 'type' in event:
            events.append(str(event['type']))
    written = sorted(str(p.relative_to(home)) for folder in (home / 'trace', home / '.codex/sessions')
                     for p in folder.rglob('*') if p.is_file())
    return dict(exit_code=code, events=events, trace_and_session_files=written,
                named_keys=[key for key in UNKNOWN if key in stdout + stderr], error_text=stderr.strip()[-2000:])


def judge(allowed, violating):
    """The exec runs' evidence -> (PASS | FAIL, why). A thread, turn or item event, or a trace or session file, means a
    session started and a model request could follow; an error event alone does not."""
    session = [e for e in violating['events'] if e.split('.')[0] in ('thread', 'turn', 'item')]
    if violating['exit_code'] in (0, None):
        return 'FAIL', f'the violating file did not fail at config load (exit {violating["exit_code"]})'
    if session or violating['trace_and_session_files']:
        return 'FAIL', 'the violating run got past config load: ' + ', '.join(
            session[:5] + violating['trace_and_session_files'][:5])
    if not violating['named_keys']:
        return 'FAIL', f'the violating file failed for another reason (exit {violating["exit_code"]})'
    if allowed['exit_code'] != 0:
        return 'FAIL', f'the 0265 config.toml run did not exit 0 (exit {allowed["exit_code"]})'
    return 'PASS', (f'the 0265 file loads and its run exits 0; the violating file fails at config load naming '
                    f'{violating["named_keys"]} with no model request')


def run_exec(runtime_path, runner=run, snapshot=None):
    runtime = json.loads(Path(runtime_path).read_text())
    target = Path(runtime['output']).parent / 'q3-strict-config.json'
    if target.exists():  # before any credential or model call
        print(f'{target} exists: Q3 is recorded once; move it aside to run again', file=sys.stderr)
        return 3
    try:
        _, blocked = (snapshot or run_cell().snapshot_auth)(runtime)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        blocked = f'credential snapshot failed: {type(exc).__name__}: {exc}'  # paths and keys, never contents
    if blocked:
        print(f'UNDECIDED: not run: {blocked}')
        return 3
    keep = Path(tempfile.mkdtemp(prefix='strict-config-exec-', dir=runtime['scratch']))
    try:
        runs = {}
        for label, text in zip(LABELS, configs()):
            home, name = exec_home(keep / label, text, runtime), f'devlyn-0265-strict-{label}-{uuid.uuid4().hex}'
            code, stdout, stderr = runner(exec_argv(runtime, home, name))
            if code is None:
                runner(['docker', 'rm', '-f', name])
            runs[label] = evidence(code, stdout, stderr, home)
        if runs['allowed']['exit_code'] == 0:  # its stderr is the session's own log, not a config error
            del runs['allowed']['error_text']
        status, why = judge(runs['allowed'], runs['violating'])
        with target.open('x') as stream:
            stream.write(json.dumps(dict(schema=1, status=status, why=why, image=runtime['image'],
                                         command=['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check',
                                                  PROMPT], unknown_keys=list(UNKNOWN), runs=runs), indent=2) + '\n')
    finally:
        for folder in Path(runtime['scratch']).glob('strict-config-exec-*'):
            shutil.rmtree(folder)
    print(f'{status}: {why}\n{target}')
    return {'PASS': 0, 'FAIL': 1}[status]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run-exec', action='store_true', required=True,
                        help='run both exec commands (one model call): the only mode')
    parser.add_argument('runtime')
    sys.exit(run_exec(parser.parse_args().runtime))
