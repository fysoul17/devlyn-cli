"""Prospective 0233 materializer with GitHub origin, fixed bootstrap and seals."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
BOOTSTRAP_DATE = '2026-10-13T00:00:00+00:00'
GITHUB_ENV = {
    'GH_CONFIG_DIR': '/run/github', 'GH_PROMPT_DISABLED': '1', 'GIT_TERMINAL_PROMPT': '0',
    'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'credential.https://github.com.helper',
    'GIT_CONFIG_VALUE_0': '!/usr/local/bin/gh auth git-credential',
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


github = load('github_rpd1_prepare', HERE / 'github.py')
base = load('defaults_rpd1', HERE.parent / '0222/prepare.py')


def bootstrap_git(work, *args):
    return github.git(work, *args, env=github.git_env() | {
        'GIT_AUTHOR_DATE': BOOTSTRAP_DATE, 'GIT_COMMITTER_DATE': BOOTSTRAP_DATE})


def codex_toml(owner):
    text = base.codex_toml(owner)
    return (text + '[shell_environment_policy]\nignore_default_excludes = false\n'
            '[shell_environment_policy.set]\n' +
            ''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in GITHUB_ENV.items()))


def verify_release(runtime):
    release = runtime['release']
    github.require(release['version'] == '4.2.18', 'release must be devlyn-cli@4.2.18')
    tarball = Path(release['tarball'])
    github.require(github.digest(tarball) == release['sha256'], 'release SHA-256 mismatch')
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(tarball.read_bytes()).digest()).decode()
    github.require(integrity == release['integrity'], 'release registry integrity mismatch')
    package = Path(runtime['control']) / 'packages/B/package'
    expected = {}
    with tarfile.open(tarball, 'r:gz') as archive:
        for member in archive.getmembers():
            if member.name == 'package' and member.isdir():
                continue
            github.require(member.name.startswith('package/'), 'unexpected release archive path')
            name = member.name.removeprefix('package/')
            if member.isdir():
                continue
            github.safe_file(package, name)
            github.require(name not in expected, 'duplicate release archive file')
            if member.isfile():
                expected[name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            else:
                github.require(member.issym(), 'unsupported release archive entry')
                expected[name] = 'link:' + member.linkname
    actual = {str(p.relative_to(package)): ('link:' + str(p.readlink()) if p.is_symlink() else github.digest(p))
              for p in package.rglob('*') if p.is_file() or p.is_symlink()}
    github.require(actual == expected and json.loads((package / 'package.json').read_text())['version'] == '4.2.18',
                   'extracted release differs from verified tarball')


def transport_state(out):
    anchor = out / 'cell/work'
    config = github.safe_file(out, 'cell/work/.git/config')
    github.require(not (anchor / '.git/commondir').exists() and
                   not (anchor / '.git/objects/info/alternates').exists(), 'foreign Git storage')
    # --no-includes prevents even reading an injected include; no participant command runs.
    settings = github.git(anchor, 'config', '--local', '--no-includes', '--null', '--list')
    keys = [row.split('\n', 1)[0].lower() for row in settings.split('\0') if row]
    forbidden = ('include.', 'includeif.', 'url.')
    github.require(not any(key.startswith(forbidden) or key in
                   ('core.sshcommand', 'extensions.worktreeconfig', 'devlyn.completionmode') for key in keys),
                   'forbidden local configuration')
    github.require(not list((anchor / '.git').rglob('config.worktree')), 'worktree config is forbidden')
    for registration in (anchor / '.git/worktrees').glob('*'):
        github.require(not registration.is_symlink() and
                       (registration / 'commondir').read_text().strip() == '../..', 'foreign worktree Git storage')
    github.require(github.git(anchor, 'remote') == 'origin', 'expected exactly one origin')
    values = [github.git(anchor, 'config', '--local', '--get-all', 'remote.origin.url'),
              github.git(anchor, 'remote', 'get-url', '--all', 'origin'),
              github.git(anchor, 'remote', 'get-url', '--push', '--all', 'origin')]
    return dict(config_sha256=github.digest(config), urls=values)


def harness_unchanged(out, baseline):
    transport = baseline['transport']
    state = transport_state(out)
    return (state == transport['local'] and state['urls'] == [github.url(transport['repository'])] * 3 and
            github.digest(out / 'harness/caller.json') == baseline['caller_sha256'] and
            github.digest(out / 'harness/roles.json') == baseline['roles_sha256'])


def prepare(runtime, name, task_id, arm, config, *, inherited, tasks, tasks_path, repository, remaining):
    github.require(arm == 'B', 'rp-d1 measures only the installed B arm')
    verify_release(runtime)
    task = next(task for task in tasks['tasks'] if task['id'] == task_id)
    route = tasks['routes'][config]
    out = Path(runtime['output']) / name
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    cell, home, harness = out / 'cell', out / 'home', out / 'harness'
    work = cell / 'work'
    for directory in (cell / 'trace', out / 'tmp', harness, home / '.codex', home / '.claude'):
        directory.mkdir(parents=True)
    # These are the inherited source, installer and raw committed-tree functions.
    # Their private git binding supplies dates only to bootstrap commits.
    inherited.source(task, runtime, work, base)
    source_sha = bootstrap_git(work, 'rev-parse', 'HEAD')
    original = inherited.committed_tree(work, source_sha)
    if runtime.get('models_cache'):
        shutil.copyfile(runtime['models_cache'], home / '.codex/models_cache.json')
    if config == 'codex':
        (home / '.codex/config.toml').write_text(codex_toml(route['owner']))
    inherited.install(runtime, work, home, config, arm)
    allocation = bootstrap_git(work, 'rev-parse', 'HEAD')
    committed = inherited.committed_tree(work, allocation)
    installed = {name: value for name, value in committed.items() if original.get(name) != value}
    github.require(bool(installed), 'installer produced no tracked files')
    request = task['request'] + ('\n\nREQUIREMENTS\n' + '\n'.join(task['obligations']) if task['obligations'] else '')
    caller = dict(request=request, allowed=task['allowed'], public_checks=task['public_checks'],
                  review_files=sorted(n for n in inherited.packet.tree(work) if inherited.packet.allowed(n, task['allowed'])),
                  original_context='', base_sha=allocation)
    (harness / 'caller.json').write_text(json.dumps(caller, indent=2))
    (harness / 'roles.json').write_text(json.dumps(dict(roles={}), indent=2) + '\n')
    github.seed(work, repository, remaining)
    bootstrap_git(work, 'remote', 'add', 'origin', github.url(repository))
    # The just-verified host seed is the exact tracking tip; no participant fetch/auth needed yet.
    bootstrap_git(work, 'update-ref', 'refs/remotes/origin/main', allocation)
    bootstrap_git(work, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
    github.require(not bootstrap_git(work, 'status', '--porcelain', '--untracked-files=all'), 'baseline is not clean')
    (out / 'prompt.txt').write_text(inherited.native_prompt(caller))
    owner = route['owner']
    env = dict(HOME='/home/participant', CODEX_HOME='/home/participant/.codex', DISABLE_AUTOUPDATER='1',
               PYTHONPATH='src:/control/python', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               CODEX_ROLLOUT_TRACE_ROOT='/cell/trace', **GITHUB_ENV)
    prompt = (out / 'prompt.txt').read_text()
    argv = (['claude', '-p', '--model', owner['model'], '--effort', owner['effort'], '--permission-mode',
             'bypassPermissions', '--output-format', 'stream-json', '--verbose', prompt] if config == 'claude' else
            ['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check', '-C', '/cell/work', prompt])
    github.write(out / 'plan.json', dict(name=name, task=task_id, arm=arm, config=config, engine=owner['engine'],
        model=owner['model'], effort=owner['effort'], wall_seconds=tasks['watchdog_seconds']['owner'], image=runtime['image'],
        cell=str(cell), tmp=str(out / 'tmp'), home=str(home), harness=str(harness),
        control=str(Path(runtime['control']) / 'public'), auth=runtime['auth'], env=env, argv=argv))
    github.write(out / 'baseline.json', dict(task=task_id, arm=arm, config=config, source_sha=source_sha,
        allocation_sha=allocation, files=committed, installed_files=installed,
        sentinel=github.record_file(work / '.user-state/draft.txt'),
        transport=dict(repository=repository, local=transport_state(out)),
        prompt_sha256=github.digest(out / 'prompt.txt'), caller_sha256=github.digest(harness / 'caller.json'),
        roles_sha256=github.digest(harness / 'roles.json'), prepare_sha256=github.digest(Path(__file__)),
        tasks_sha256=github.digest(tasks_path)))
    return out
