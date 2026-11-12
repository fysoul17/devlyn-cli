"""Materialize one 0265 cell: prepare.py <runtime.json> <name> <task> <arm> <config>. Never dispatches models.

Arms: A starts the engine raw; B starts the same arguments through `devlyn run` of the frozen package, which the owner
container mounts read-only at /install (plan['install']). Nothing is installed in the tree. All use the same native
prompt.

Layout under <output>/<name>: cell/ (container /cell: the anchor repository cell/work, linked worktrees, trace/),
tmp/ (/tmp, preserved: an owner may allocate its worktree there), home/ (/home/participant) and harness/
(/harness, read-only: roles, caller contract and local mirror).
"""
import hashlib
import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import re
import tomllib

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / '0222'
TASKS_PATH = HERE.parent / '0233/tasks.json'
TASKS = json.loads(TASKS_PATH.read_text())
_spec = importlib.util.spec_from_file_location('packet0222', BASE / 'packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
_spec = importlib.util.spec_from_file_location('locate0231p', HERE.parent / '0233/locate.py')
locate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locate)
# Reuse 0222's source materialization (registered inputs or the pinned clone, participant identity, .devlyn/ excluded).
_spec = importlib.util.spec_from_file_location('prepare0222', BASE / 'prepare.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
ARMS = ('A', 'B')
CONFIGS = ('claude', 'codex')
TASK_IDS = ('D3', 'D4', 'B5', 'F10', 'F11', 'SMOKE')
WALL_SECONDS = 2700  # owner watchdog, both arms (DESIGN "Arms")
DEVLYN = ['node', '/install/package/bin/devlyn.js', 'run']


def git(work, *args):
    return subprocess.run(['git', *args], cwd=work, check=True, capture_output=True, text=True).stdout.strip()


def source(task, runtime, work, base):
    if task['id'] not in ('F10', 'F11'):
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
    git(work, 'add', '-f', '-A', 'node_modules')
    git(work, 'commit', '-qm', 'registered inputs with vendored dependencies')
    with (work / '.git/info/exclude').open('a') as exclude:
        exclude.write('.devlyn/\n')


def override_tasks(path=None):
    """Only D3/D4 issue hashes may change; snapshot metadata is mandatory."""
    path = Path(path or HERE.parent / '0256/tasks-override.json')
    overrides = json.loads(path.read_text())
    if not isinstance(overrides, dict) or set(overrides) != {'D3', 'D4'}:
        raise ValueError('issue override must contain exactly D3 and D4')
    tasks = json.loads(TASKS_PATH.read_text())
    urls = {'D3': 'https://api.github.com/repos/tj/commander.js/issues/2530',
            'D4': 'https://api.github.com/repos/pallets/click/issues/2645'}
    for task in tasks['tasks']:
        if task['id'] not in urls:
            continue
        entry = overrides[task['id']]
        if (not isinstance(entry, dict) or set(entry) != {'issue_snapshot_sha256', 'fetched_at', 'url'}
                or not isinstance(entry['issue_snapshot_sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', entry['issue_snapshot_sha256'])
                or not isinstance(entry['fetched_at'], str)
                or entry['url'] != urls[task['id']]):
            raise ValueError(task['id'] + ' issue override malformed')
        try:
            fetched = datetime.datetime.fromisoformat(entry['fetched_at'])
        except ValueError as exc:
            raise ValueError(task['id'] + ' issue override malformed') from exc
        if fetched.utcoffset() != datetime.timedelta(0) or not entry['fetched_at'].endswith('+00:00'):
            raise ValueError(task['id'] + ' issue override malformed')
        task['issue_snapshot_sha256'] = entry['issue_snapshot_sha256']
    return tasks


def codex_config(owner):
    """The Codex config.toml of both arms: 0222's for the route with `remote_plugin = false` in place of
    `plugins = false` (devlyn run's session plugin needs plugins on; Codex's own curated remote plugins stay out of the
    model input, DESIGN "Arms", O10), A getting the same file, and the trust entry moved to the cell's working tree
    (0237)."""
    text = base.codex_toml(owner).replace('plugins = false\n', 'remote_plugin = false\n')
    features = tomllib.loads(text).get('features', {})
    if 'plugins = false' in text or 'plugins' in features or features.get('remote_plugin') is not False:
        raise ValueError('Codex config still disables plugins or leaves remote plugins on')
    inherited = '[projects."/work"]'
    if (text.count(inherited) != 1 or tomllib.loads(text).get('projects') !=
            {'/work': {'trust_level': 'trusted'}}):
        raise ValueError('unexpected inherited Codex project trust')
    return text.replace(inherited, '[projects."/cell/work"]')


def owner_argv(config, owner, prompt):
    """O(engine) of DESIGN "Arms": the same owner arguments in both arms."""
    if config == 'claude':
        return ['-p', '--model', owner['model'], '--effort', owner['effort'], '--permission-mode', 'bypassPermissions',
                '--output-format', 'stream-json', '--verbose', prompt]
    return ['exec', '--json', '--skip-git-repo-check', prompt]


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
    files stay behind in the anchor; export attributes do not apply)."""
    with tempfile.TemporaryDirectory() as temp:
        return packet.tree(locate.raw_tree(['git', '-C', str(work)], sha, Path(temp)))


def match_committed_tree(work, committed):
    """Give tracked regular files their committed modes and refuse any remaining baseline difference."""
    for name, value in committed.items():
        if value.startswith('link:'):
            continue
        path = work / name
        if path.is_file() and not path.is_symlink():
            path.chmod(int(value.rsplit(':', 1)[1], 8))
    actual = packet.tree(work)
    if {name: actual.get(name) for name in committed} != committed:
        raise ValueError('working tree differs from committed tree')


def native_prompt(caller):
    """0222's native prompt (its DESIGN "A (native)"): the task frame plus the caller contract, with 0231's paths."""
    return (HERE.parent / '0232/common.txt').read_text() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def prepare(runtime, name, task_id, arm, config):
    if task_id not in TASK_IDS or arm not in ARMS or config not in CONFIGS:
        raise ValueError(f'0265 cells are {"/".join(TASK_IDS)} x arm A/B x config claude/codex')
    override_path = Path(runtime.get('tasks_override', HERE.parent / '0256/tasks-override.json'))
    tasks = override_tasks(override_path)
    task = next(t for t in tasks['tasks'] if t['id'] == task_id)
    route = TASKS['routes'][config]
    out = Path(runtime['output']) / name
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    out.chmod(0o700)
    cell, home, harness = out / 'cell', out / 'home', out / 'harness'
    work = cell / 'work'
    cell.mkdir()
    (cell / 'trace').mkdir()
    (out / 'tmp').mkdir()
    harness.mkdir()
    source(task, runtime, work, base)
    source_sha = git(work, 'rev-parse', 'HEAD')
    (home / '.codex').mkdir(parents=True)
    (home / '.claude').mkdir()
    if runtime.get('models_cache'):
        shutil.copyfile(runtime['models_cache'], home / '.codex/models_cache.json')
    if config == 'codex':
        (home / '.codex/config.toml').write_text(codex_config(route['owner']))
    files = committed_tree(work, git(work, 'rev-parse', 'HEAD'))
    match_committed_tree(work, files)
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
               PYTHONPATH='src:/control/python', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               CODEX_ROLLOUT_TRACE_ROOT='/cell/trace', MYPY_CACHE_DIR='/tmp/.mypy_cache',
               ENABLE_CLAUDEAI_MCP_SERVERS='false')
    prompt = (out / 'prompt.txt').read_text()
    argv = ([] if arm == 'A' else DEVLYN) + [owner['engine'], *owner_argv(config, owner, prompt)]
    settings = home / '.claude/settings.json'
    settings.write_text(json.dumps(dict(syncClaudeAiSkills=False, syncClaudeAiPlugins=False)) + '\n')
    plan = dict(name=name, task=task_id, arm=arm, config=config, engine=owner['engine'], model=owner['model'],
                effort=owner['effort'], wall_seconds=WALL_SECONDS, image=runtime['image'],
                cell=str(cell), tmp=str(out / 'tmp'), home=str(home), harness=str(harness),
                control=str(Path(runtime['control']) / 'public'), auth=runtime['auth'],
                install=str(Path(runtime['control']) / 'packages' / 'B') if arm == 'B' else None, env=env, argv=argv)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'baseline.json').write_text(json.dumps(dict(
        task=task_id, arm=arm, config=config, source_sha=source_sha, allocation_sha=transport['head'],
        transport=transport, files=files,
        prompt_sha256=digest(out / 'prompt.txt'), caller_sha256=digest(harness / 'caller.json'),
        roles_sha256=digest(harness / 'roles.json'), prepare_sha256=digest(Path(__file__)),
        tasks_sha256=digest(TASKS_PATH), override_sha256=digest(override_path),
        prepared={str(path.relative_to(out)): digest(path) for path in
                  [out / 'plan.json', out / 'prompt.txt', settings] +
                  ([home / '.codex/config.toml'] if config == 'codex' else [])}), indent=2))
    return out


if __name__ == '__main__':
    print(prepare(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:6]))
