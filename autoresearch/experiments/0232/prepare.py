"""Materialize one 0232 cell: prepare.py <runtime.json> <name> <task> <arm> <config>. Never dispatches models.

Arms: A is the task repository as supplied with the native prompt (0222's task frame plus the caller contract); I
installs the rung-1 package and gets A's prompt; F is 0231's control arm (4.1.0 resolve, unchanged).

Layout under <output>/<name>: cell/ (container /cell: the anchor repository cell/work, linked worktrees, trace/),
tmp/ (/tmp, preserved: an owner may allocate its worktree there), home/ (/home/participant) and harness/
(/harness, read-only: roles, caller contract, Git transport and mirror).
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / '0222'
TASKS = json.loads((BASE / 'tasks.json').read_text())  # 0222's registered tasks, routes and watchdogs
_spec = importlib.util.spec_from_file_location('packet0222', BASE / 'packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
_spec = importlib.util.spec_from_file_location('locate0231p', HERE / 'locate.py')
locate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locate)
ARMS = ('A', 'I', 'F')
REVIEW = '.devlyn/review.js'  # the rung-1 review launcher, installed under the participant's home
INSTALL = {'claude': ['-y', '--claude'], 'codex': ['-y']}
GOAL = '.task/goal.txt'
MAX_ROUNDS = 4
TRANSPORT = '''#!/bin/sh
# Harness Git transport for the cell's GitHub origin: fetches come from the sealed mirror beside this script (/harness
# in the cell); everything else is refused.
for last; do :; done
case "$last" in
  "git-upload-pack '{repo}.git'"|"git-upload-pack '/{repo}.git'") exec git-upload-pack "${0%/*}/mirror.git" ;;
esac
echo "harness transport refused: $last" >&2
exit 128
'''


def git(work, *args):
    return subprocess.run(['git', *args], cwd=work, check=True, capture_output=True, text=True).stdout.strip()


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


def goal_text(task):
    """0222's product goal; its caller contract moves to the read-only /harness so it resolves from any worktree."""
    request = task['request'] + ('\n\nREQUIREMENTS\n' + '\n'.join(task['obligations']) if task['obligations'] else '')
    common = (HERE / 'common.txt').read_text()
    return (request + '\n\nALLOWED PATHS\n' + '\n'.join(task['allowed']) + '\n\nPUBLIC CHECKS\n'
            + '\n'.join(task['public_checks']) + '\n\nCONSTRAINTS\n' + common
            + 'Local-only: do not push or open a pull request.\n'), request


def mirror(work, harness, repository):
    """A bare mirror whose only ref and HEAD are main at the allocation commit, served by the sealed transport script."""
    head = git(work, 'rev-parse', 'HEAD')
    target = harness / 'mirror.git'
    subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(target)], check=True)
    subprocess.run(['git', '-C', str(target), 'config', 'receive.shallowUpdate', 'true'], check=True)  # D3/D4 sources are shallow
    subprocess.run(['git', '-C', str(work), 'push', '-q', str(target), f'{head}:refs/heads/main'], check=True)
    script = harness / 'git-ssh'
    script.write_text(TRANSPORT.replace('{repo}', repository))
    script.chmod(0o755)
    return dict(head=head, refs=git(target, 'for-each-ref', '--format=%(refname) %(objectname)'),
                objects=hashlib.sha256(git(target, 'rev-list', '--objects', '--all').encode()).hexdigest(),
                script_sha256=hashlib.sha256(script.read_bytes()).hexdigest())


def committed_tree(work, sha):
    """packet.tree of a commit's tracked files from its raw objects: what allocation gives a linked worktree (ignored
    installer output stays behind in the anchor; export attributes do not apply)."""
    with tempfile.TemporaryDirectory() as temp:
        return packet.tree(locate.raw_tree(['git', '-C', str(work)], sha, Path(temp)))


def prompt_text(config):
    command = f'/devlyn-resolve --goal-file {GOAL} --role-config /harness/roles.json --max-rounds {MAX_ROUNDS}'
    return command if config == 'claude' else (
        'Read /cell/work/.agents/skills/devlyn-resolve/SKILL.md and execute ' + command.removeprefix('/'))


def native_prompt(caller):
    """0222's native prompt (its DESIGN "A (native)"): the task frame plus the caller contract, with 0231's paths."""
    return (HERE / 'common.txt').read_text() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def prepare(runtime, name, task_id, arm, config):
    task = next(t for t in TASKS['tasks'] if t['id'] == task_id)
    route = TASKS['routes'][config]
    if arm not in ARMS:
        raise ValueError('arm must be A, I or F')
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
    base.source(task, runtime, work)
    source_sha = git(work, 'rev-parse', 'HEAD')
    (home / '.codex').mkdir(parents=True)
    (home / '.claude').mkdir()
    if runtime.get('models_cache'):
        shutil.copyfile(runtime['models_cache'], home / '.codex/models_cache.json')
    if config == 'codex':
        (home / '.codex/config.toml').write_text(base.codex_toml(route['owner']))
    if arm != 'A':
        install(runtime, work, home, config, arm)
    if arm == 'I' and not (home / REVIEW).is_file():
        raise ValueError('the I package installed no review launcher at $HOME/' + REVIEW)
    goal, request = goal_text(task)
    if arm == 'F':
        (work / GOAL).parent.mkdir()
        (work / GOAL).write_text(goal)
        git(work, 'add', GOAL)
        git(work, 'commit', '-qm', 'task goal')
    issue = Path(runtime['sources']) / f'{task_id}-issue.json'
    if 'issue_snapshot_sha256' in task and hashlib.sha256(issue.read_bytes()).hexdigest() != task['issue_snapshot_sha256']:
        raise ValueError(task_id + ' issue snapshot changed')
    caller = dict(request=request, allowed=task['allowed'], public_checks=task['public_checks'],
                  review_files=sorted(n for n in packet.tree(work) if packet.allowed(n, task['allowed'])),
                  original_context=issue.read_text() if 'issue_snapshot_sha256' in task else '',
                  base_sha=git(work, 'rev-parse', 'HEAD'))
    (harness / 'caller.json').write_text(json.dumps(caller, indent=2))
    (harness / 'roles.json').write_text(json.dumps(dict(roles=route['product_roles']), indent=2) + '\n')
    git(work, 'remote', 'add', 'origin', f'git@github.com:{task["repository"]}.git')
    git(work, 'config', 'core.sshCommand', '/harness/git-ssh')
    transport = mirror(work, harness, task['repository'])
    for args in (('fetch', '-q', 'origin'), ('remote', 'set-head', 'origin', '-a')):  # origin/HEAD: the launcher's base
        subprocess.run(['git', '-c', 'core.sshCommand=' + shlex.quote(str(harness / 'git-ssh')), *args], cwd=work,
                       check=True, capture_output=True, env=locate.ENV)
    if git(work, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('baseline is not clean')
    (out / 'prompt.txt').write_text(prompt_text(config) if arm == 'F' else native_prompt(caller))
    owner = route['owner']
    env = dict(HOME='/home/participant', CODEX_HOME='/home/participant/.codex', DISABLE_AUTOUPDATER='1',
               PYTHONPATH='src:/control/python', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               CODEX_ROLLOUT_TRACE_ROOT='/cell/trace', MYPY_CACHE_DIR='/tmp/.mypy_cache')
    prompt = (out / 'prompt.txt').read_text()
    argv = (['claude', '-p', '--model', owner['model'], '--effort', owner['effort'], '--permission-mode',
             'bypassPermissions', '--output-format', 'stream-json', '--verbose', prompt] if config == 'claude' else
            ['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check', '-C', '/cell/work', prompt])
    plan = dict(name=name, task=task_id, arm=arm, config=config, engine=owner['engine'], model=owner['model'],
                effort=owner['effort'], wall_seconds=TASKS['watchdog_seconds']['owner'], image=runtime['image'],
                cell=str(cell), tmp=str(out / 'tmp'), home=str(home), harness=str(harness),
                control=str(Path(runtime['control']) / 'public'), auth=runtime['auth'], env=env, argv=argv)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'baseline.json').write_text(json.dumps(dict(
        task=task_id, arm=arm, config=config, source_sha=source_sha, allocation_sha=transport['head'],
        transport=transport, files=committed_tree(work, transport['head']),
        goal_sha256=digest(work / GOAL) if arm == 'F' else None,
        review_sha256=digest(home / REVIEW) if arm == 'I' else None,
        prompt_sha256=digest(out / 'prompt.txt'), caller_sha256=digest(harness / 'caller.json'),
        roles_sha256=digest(harness / 'roles.json'), prepare_sha256=digest(Path(__file__)),
        tasks_sha256=digest(BASE / 'tasks.json')), indent=2))
    return out


if __name__ == '__main__':
    print(prepare(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:6]))
