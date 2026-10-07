"""Materialize one 0234 cell: prepare.py <runtime.json> <name> <task> <arm> <config>. Never dispatches models.

Arms: A is native; B, H and P install their pinned packages. All use the same native prompt.

Layout under <output>/<name>: cell/ (container /cell: the anchor repository cell/work, linked worktrees, trace/),
tmp/ (/tmp, preserved: an owner may allocate its worktree there), home/ (/home/participant) and harness/
(/harness, read-only: roles, caller contract and local mirror).
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / '0222'
TASKS = json.loads((HERE / 'tasks.json').read_text())
_spec = importlib.util.spec_from_file_location('packet0222', BASE / 'packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
_spec = importlib.util.spec_from_file_location('locate0231p', HERE / 'locate.py')
locate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locate)
ARMS = ('A', 'B', 'H', 'P')
INSTALL = {'claude': ['-y', '--claude'], 'codex': ['-y']}


def git(work, *args):
    return subprocess.run(['git', *args], cwd=work, check=True, capture_output=True, text=True).stdout.strip()


def source(task, runtime, work, base):
    if task['id'] not in ('F16', 'F23', 'F25', 'F10', 'F11', 'E1', 'E2', 'S2'):
        return base.source(task, runtime, work)
    # The vendored package binaries contain symlinks. Preserve them when sealing the participant base.
    shutil.copytree(HERE.parents[2] / task['source_dir'], work, symlinks=True)
    if packet.content(packet.tree(work)) != task['source_sha256']:
        raise ValueError(task['id'] + ' registered inputs changed')
    git(work, 'init', '-q', '-b', 'main')
    for key, value in (('user.name', 'Participant'), ('user.email', 'participant@localhost'),
                       ('commit.gpgsign', 'false')):
        git(work, 'config', key, value)
    git(work, 'add', '-A')
    if (work / 'node_modules').exists():
        git(work, 'add', '-f', '-A', 'node_modules')
    git(work, 'commit', '-qm', 'registered inputs with vendored dependencies')
    with (work / '.git/info/exclude').open('a') as exclude:
        exclude.write('.devlyn/\n')


def install(runtime, work, home, config, arm):
    """The arm's own installer, offline, in the cell image, seeing only its own package; its output is the baseline."""
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--env', 'HOME=/home/participant', '-w', '/work',
                    '--mount', f'type=bind,src={work},dst=/work', '--mount', f'type=bind,src={home},dst=/home/participant',
                    '--mount', f'type=bind,src={Path(runtime["control"]) / "packages" / arm},dst=/install,readonly',
                    runtime['image'], 'node', '/install/package/bin/devlyn.js', *INSTALL[config]],
                   check=True, capture_output=True, timeout=300)
    git(work, 'add', '-A')
    git(work, 'commit', '-qm', 'install ' + arm)

def mirror(work, harness):
    """A sealed local bare origin at the allocation commit, without a GitHub transport."""
    head = git(work, 'rev-parse', 'HEAD')
    target = harness / 'mirror.git'
    subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(target)], check=True)
    subprocess.run(['git', '-C', str(target), 'config', 'receive.shallowUpdate', 'true'], check=True)
    subprocess.run(['git', '-C', str(work), 'push', '-q', str(target), f'{head}:refs/heads/main'], check=True)
    return dict(head=head, refs=git(target, 'for-each-ref', '--format=%(refname) %(objectname)'),
                objects=hashlib.sha256(git(target, 'rev-list', '--objects', '--all').encode()).hexdigest())


def committed_tree(work, sha):
    """packet.tree of a commit's tracked files from its raw objects: what allocation gives a linked worktree (ignored
    installer output stays behind in the anchor; export attributes do not apply)."""
    with tempfile.TemporaryDirectory() as temp:
        return packet.tree(locate.raw_tree(['git', '-C', str(work)], sha, Path(temp)))

def native_prompt(caller):
    """0222's native prompt (its DESIGN "A (native)"): the task frame plus the caller contract, with 0231's paths."""
    return (HERE.parent / '0232/common.txt').read_text() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def prepare(runtime, name, task_id, arm, config):
    task = next(t for t in TASKS['tasks'] if t['id'] == task_id)
    route = TASKS['routes'][config]
    if arm not in ARMS:
        raise ValueError('arm must be A, B, H or P')
    out = Path(runtime['output']) / name
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    out.chmod(0o700)
    cell, home, harness = out / 'cell', out / 'home', out / 'harness'
    work = cell / 'work'
    cell.mkdir()
    (cell / 'trace').mkdir()
    (out / 'tmp').mkdir()
    harness.mkdir()
    # Reuse 0222's source materialization (registered inputs or the pinned clone, participant identity, .devlyn/ excluded).
    _source = importlib.util.spec_from_file_location('prepare0222', BASE / 'prepare.py')
    base = importlib.util.module_from_spec(_source)
    _source.loader.exec_module(base)
    source(task, runtime, work, base)
    source_sha = git(work, 'rev-parse', 'HEAD')
    (home / '.codex').mkdir(parents=True)
    (home / '.claude').mkdir()
    if runtime.get('models_cache'):
        shutil.copyfile(runtime['models_cache'], home / '.codex/models_cache.json')
    if arm != 'A':
        install(runtime, work, home, config, arm)
    # Both peer CLIs take their defaults from the same per-cell home, for every arm.
    # The Codex owner still receives the registered native-child route in this config.
    codex_owner = TASKS['routes']['codex']['owner']
    (home / '.codex/config.toml').write_text(base.codex_toml(codex_owner))
    (home / '.claude/settings.json').write_text(json.dumps({
        'model': TASKS['routes']['claude']['owner']['model'], 'effortLevel': 'high'}) + '\n')
    request = task['request'] + ('\n\nREQUIREMENTS\n' + '\n'.join(task['obligations']) if task['obligations'] else '')
    issue = Path(runtime['sources']) / f'{task_id}-issue.json'
    if 'issue_snapshot_sha256' in task and hashlib.sha256(issue.read_bytes()).hexdigest() != task['issue_snapshot_sha256']:
        raise ValueError(task_id + ' issue snapshot changed')
    caller = dict(request=request, allowed=task['allowed'], public_checks=task['public_checks'],
                  review_files=sorted(n for n in packet.tree(work) if packet.allowed(n, task['allowed'])),
                  original_context=issue.read_text() if 'issue_snapshot_sha256' in task else '',
                  base_sha=git(work, 'rev-parse', 'HEAD'))
    (harness / 'caller.json').write_text(json.dumps(caller, indent=2))
    (harness / 'roles.json').write_text(json.dumps(dict(roles=route['product_roles']), indent=2) + '\n')
    transport = mirror(work, harness)
    git(work, 'remote', 'add', 'origin', '/harness/mirror.git')
    subprocess.run(['git', 'fetch', '-q', str(harness / 'mirror.git'),
                    '+refs/heads/main:refs/remotes/origin/main'],
                   cwd=work, check=True, capture_output=True, env=locate.ENV)
    git(work, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
    if git(work, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('baseline is not clean')
    (out / 'prompt.txt').write_text(native_prompt(caller))
    owner = route['owner']
    env = dict(HOME='/home/participant', CODEX_HOME='/home/participant/.codex', DISABLE_AUTOUPDATER='1',
               CLAUDE_CODE_EFFORT_LEVEL='high',
               PYTHONPATH='src:/control/python', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               CODEX_ROLLOUT_TRACE_ROOT='/cell/trace', MYPY_CACHE_DIR='/tmp/.mypy_cache')
    prompt = (out / 'prompt.txt').read_text()
    argv = (['claude', '-p', '--model', owner['model'], '--effort', owner['effort'], '--permission-mode',
             'bypassPermissions', '--output-format', 'stream-json', '--verbose', prompt] if config == 'claude' else
            ['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check', '-C', '/cell/work', prompt])
    plan = dict(name=name, task=task_id, arm=arm, config=config, engine=owner['engine'], model=owner['model'],
                peer_route=route['peer_routes'].get(arm),
                effort=owner['effort'], wall_seconds=TASKS['watchdog_seconds']['owner'], image=runtime['image'],
                cell=str(cell), tmp=str(out / 'tmp'), home=str(home), harness=str(harness),
                control=str(Path(runtime['control']) / 'public'), auth=runtime['auth'], env=env, argv=argv)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'baseline.json').write_text(json.dumps(dict(
        task=task_id, arm=arm, config=config, source_sha=source_sha, allocation_sha=transport['head'],
        transport=transport, files=committed_tree(work, transport['head']),
        prompt_sha256=digest(out / 'prompt.txt'), caller_sha256=digest(harness / 'caller.json'),
        roles_sha256=digest(harness / 'roles.json'), prepare_sha256=digest(Path(__file__)),
        tasks_sha256=digest(HERE / 'tasks.json')), indent=2))
    return out


if __name__ == '__main__':
    print(prepare(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:6]))
